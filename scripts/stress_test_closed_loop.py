import argparse
import asyncio
import json
import random
import statistics
import string
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


@dataclass
class RunConfig:
    api_base_url: str
    total_records: int
    concurrency: int
    timeout_seconds: float
    include_tracking: bool
    tracking_poll_attempts: int
    tracking_poll_interval_seconds: float
    output_report: Path
    output_events: Path


@dataclass
class RequestResult:
    external_id: str
    status: str
    latency_ms: float
    suggestion_confidence: float | None
    manual_override: bool | None
    error: str | None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _random_suffix(size: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(size))


def _critical_template(index: int) -> tuple[str, str]:
    samples = [
        (
            f"Riesgo de vida por semaforo fuera de servicio {index}",
            "Se reporta accidente recurrente y riesgo de vida por semaforo dañado. Se solicita accion inmediata por vencimiento legal en 2 dias.",
        ),
        (
            f"Riesgo de salud por aguas residuales {index}",
            "Hay afectacion de salud publica por aguas residuales. Solicitud urgente por terminos de ley por vencer en menos de 3 dias.",
        ),
        (
            f"Bache profundo con lesionados {index}",
            "Ciudadanos lesionados por bache profundo. Se requiere intervencion de emergencia y respuesta inmediata.",
        ),
    ]
    return random.choice(samples)


def _normal_template(index: int) -> tuple[str, str]:
    samples = [
        (
            f"Mantenimiento de luminarias comuna 17 {index}",
            "Se reportan luminarias apagadas en corredor peatonal. Solicito reparacion y verificacion nocturna.",
        ),
        (
            f"Hueco en via secundaria {index}",
            "Se solicita reparacion de hueco para prevenir danos vehiculares y congestion.",
        ),
        (
            f"Solicitud poda preventiva {index}",
            "Arbol con ramas sobre via peatonal; se solicita poda preventiva y evaluacion tecnica.",
        ),
    ]
    return random.choice(samples)


def build_payload(index: int) -> dict[str, Any]:
    is_critical = (index % 10) == 0
    topic, content = _critical_template(index) if is_critical else _normal_template(index)
    return {
        "citizen_name": f"Ciudadano Stress {index}",
        "citizen_id": f"CC-{10000000 + index}",
        "citizen_email": f"stress{index}@cali.gov.co",
        "citizen_phone": f"300{index % 10000000:07d}",
        "citizen_address": f"Comuna {(index % 22) + 1}, Santiago de Cali",
        "topic": topic,
        "content": content,
    }


async def suggest_dependency(client: httpx.AsyncClient, api_base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(
        f"{api_base_url}/api/v1/master-data/suggest-dependency",
        json={
            "topic": payload["topic"],
            "content": payload["content"],
            "minimum_confidence": 0.85,
        },
    )
    response.raise_for_status()
    return response.json()


async def submit_citizen(client: httpx.AsyncClient, api_base_url: str, payload: dict[str, Any], suggestion: dict[str, Any]) -> dict[str, Any]:
    form_data = {
        "citizen_name": payload["citizen_name"],
        "citizen_id": payload["citizen_id"],
        "citizen_email": payload["citizen_email"],
        "content": payload["content"],
        "pqrs_type_id": "PETICION_GENERAL",
        "selected_dependency_id": suggestion.get("suggested_dependency_id") or "",
        "suggested_dependency_id": suggestion.get("suggested_dependency_id") or "",
        "routing_confidence_score": str(suggestion.get("confidence_score") or 0),
    }
    response = await client.post(f"{api_base_url}/api/v1/citizen/submit", data=form_data)
    response.raise_for_status()
    return response.json()


async def track_status(
    client: httpx.AsyncClient,
    api_base_url: str,
    external_id: str,
    attempts: int,
    interval_seconds: float,
) -> dict[str, Any] | None:
    for _ in range(attempts):
        response = await client.get(f"{api_base_url}/api/v1/public/track/{external_id}")
        if response.status_code == 200:
            return response.json()
        if response.status_code == 404:
            await asyncio.sleep(interval_seconds)
            continue
        response.raise_for_status()
    return None


def build_event_timeline(external_id: str, suggestion: dict[str, Any], submit_result: dict[str, Any], track_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    confidence = suggestion.get("confidence_score", 0)
    dependency = suggestion.get("suggested_dependency_name") or suggestion.get("suggested_dependency_id") or "SIN_DEPENDENCIA"
    base_events = [
        {
            "event": "INGEST_RECEIVED",
            "stage": "ingesta",
            "status": "OK",
            "external_id": external_id,
            "timestamp": _now_iso(),
            "metadata": {"channel": "portal_ciudadano"},
        },
        {
            "event": "CLASSIFICATION_COMPLETED",
            "stage": "clasificacion",
            "status": "OK",
            "external_id": external_id,
            "timestamp": _now_iso(),
            "metadata": {
                "dependency": dependency,
                "confidence": confidence,
                "autoselect": suggestion.get("should_autoselect", False),
            },
        },
        {
            "event": "LEGAL_AUDIT_REQUESTED",
            "stage": "auditoria_juridica",
            "status": "OK",
            "external_id": external_id,
            "timestamp": _now_iso(),
            "metadata": {"simulated": False},
        },
        {
            "event": "IMMUTABLE_SIGNING_PENDING",
            "stage": "firma_inmutable",
            "status": "PENDING",
            "external_id": external_id,
            "timestamp": _now_iso(),
            "metadata": {},
        },
        {
            "event": "OPERATIONAL_ORDER_PENDING",
            "stage": "orden_operativa",
            "status": "PENDING",
            "external_id": external_id,
            "timestamp": _now_iso(),
            "metadata": {},
        },
    ]

    if track_result:
        base_events.append(
            {
                "event": "TRACKING_VISIBLE",
                "stage": "cierre",
                "status": "OK",
                "external_id": external_id,
                "timestamp": _now_iso(),
                "metadata": {
                    "estado": track_result.get("estado"),
                    "ledger_tx": (track_result.get("certificacion_ledger") or {}).get("transaction_id"),
                },
            }
        )

    return base_events


async def process_one(
    index: int,
    client: httpx.AsyncClient,
    config: RunConfig,
    semaphore: asyncio.Semaphore,
    events_sink: list[dict[str, Any]],
) -> RequestResult:
    async with semaphore:
        payload = build_payload(index)
        start = time.perf_counter()
        try:
            suggestion = await suggest_dependency(client, config.api_base_url, payload)
            submit_result = await submit_citizen(client, config.api_base_url, payload, suggestion)

            external_id = submit_result.get("radicado") or f"UNSET-{_random_suffix()}"
            track_result = None
            if config.include_tracking:
                track_result = await track_status(
                    client,
                    config.api_base_url,
                    external_id,
                    config.tracking_poll_attempts,
                    config.tracking_poll_interval_seconds,
                )

            events_sink.extend(build_event_timeline(external_id, suggestion, submit_result, track_result))

            latency_ms = (time.perf_counter() - start) * 1000
            return RequestResult(
                external_id=external_id,
                status="OK",
                latency_ms=latency_ms,
                suggestion_confidence=suggestion.get("confidence_score"),
                manual_override=submit_result.get("manual_override"),
                error=None,
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - start) * 1000
            external_id = f"FAILED-{_random_suffix()}"
            events_sink.append(
                {
                    "event": "FLOW_FAILED",
                    "stage": "error",
                    "status": "ERROR",
                    "external_id": external_id,
                    "timestamp": _now_iso(),
                    "metadata": {"error": str(exc), "index": index},
                }
            )
            return RequestResult(
                external_id=external_id,
                status="ERROR",
                latency_ms=latency_ms,
                suggestion_confidence=None,
                manual_override=None,
                error=str(exc),
            )


async def run(config: RunConfig) -> dict[str, Any]:
    config.output_report.parent.mkdir(parents=True, exist_ok=True)
    config.output_events.parent.mkdir(parents=True, exist_ok=True)

    limits = httpx.Limits(max_connections=config.concurrency * 2, max_keepalive_connections=config.concurrency)
    timeout = httpx.Timeout(config.timeout_seconds)

    semaphore = asyncio.Semaphore(config.concurrency)
    events_sink: list[dict[str, Any]] = []

    started_at = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        tasks = [
            asyncio.create_task(process_one(i, client, config, semaphore, events_sink))
            for i in range(1, config.total_records + 1)
        ]
        results = await asyncio.gather(*tasks)
    total_seconds = time.perf_counter() - started_at

    ok_results = [r for r in results if r.status == "OK"]
    err_results = [r for r in results if r.status != "OK"]
    latencies = [r.latency_ms for r in ok_results]
    confidences = [r.suggestion_confidence for r in ok_results if r.suggestion_confidence is not None]

    report = {
        "suite": "orbital-prime-closed-loop-stress",
        "timestamp": _now_iso(),
        "api_base_url": config.api_base_url,
        "total_records": config.total_records,
        "concurrency": config.concurrency,
        "duration_seconds": round(total_seconds, 2),
        "throughput_rps": round((len(ok_results) + len(err_results)) / total_seconds, 2) if total_seconds else 0,
        "success_count": len(ok_results),
        "error_count": len(err_results),
        "success_rate": round((len(ok_results) / config.total_records) * 100, 2) if config.total_records else 0,
        "latency_ms": {
            "p50": round(statistics.median(latencies), 2) if latencies else None,
            "p95": round(statistics.quantiles(latencies, n=20)[18], 2) if len(latencies) >= 20 else None,
            "avg": round(statistics.mean(latencies), 2) if latencies else None,
            "max": round(max(latencies), 2) if latencies else None,
        },
        "legal_confidence": {
            "avg": round(statistics.mean(confidences), 4) if confidences else None,
            "min": round(min(confidences), 4) if confidences else None,
            "max": round(max(confidences), 4) if confidences else None,
        },
        "errors": [asdict(r) for r in err_results[:100]],
    }

    config.output_report.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with config.output_events.open("w", encoding="utf-8") as events_file:
        for event in events_sink:
            events_file.write(json.dumps(event, ensure_ascii=True) + "\n")

    return report


def parse_args() -> RunConfig:
    parser = argparse.ArgumentParser(description="Stress test for Orbital Prime closed-loop flow")
    parser.add_argument("--api-base-url", default="http://localhost:8000", help="Base URL for FastAPI backend")
    parser.add_argument("--records", type=int, default=40000, help="Total records to send")
    parser.add_argument("--concurrency", type=int, default=80, help="Concurrent in-flight requests")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds")
    parser.add_argument("--include-tracking", action="store_true", help="Poll public tracking endpoint after submit")
    parser.add_argument("--tracking-attempts", type=int, default=3, help="Tracking retries per record")
    parser.add_argument("--tracking-interval", type=float, default=0.5, help="Delay between tracking retries")
    parser.add_argument(
        "--output-report",
        default="documentacion/STRESS_REPORT_CLOSED_LOOP.json",
        help="JSON report output file",
    )
    parser.add_argument(
        "--output-events",
        default="documentacion/telemetry_events.ndjson",
        help="NDJSON telemetry output file",
    )
    args = parser.parse_args()

    return RunConfig(
        api_base_url=args.api_base_url.rstrip("/"),
        total_records=args.records,
        concurrency=args.concurrency,
        timeout_seconds=args.timeout,
        include_tracking=args.include_tracking,
        tracking_poll_attempts=args.tracking_attempts,
        tracking_poll_interval_seconds=args.tracking_interval,
        output_report=Path(args.output_report),
        output_events=Path(args.output_events),
    )


def main() -> None:
    config = parse_args()
    report = asyncio.run(run(config))

    print("=" * 60)
    print("ORBITAL PRIME CLOSED-LOOP STRESS TEST")
    print("=" * 60)
    print(f"Records: {report['total_records']}")
    print(f"Concurrency: {report['concurrency']}")
    print(f"Success rate: {report['success_rate']}%")
    print(f"Throughput: {report['throughput_rps']} req/s")
    print(f"Latency p50/p95: {report['latency_ms']['p50']} / {report['latency_ms']['p95']} ms")
    print(f"Output report: {config.output_report}")
    print(f"Output events: {config.output_events}")


if __name__ == "__main__":
    main()
