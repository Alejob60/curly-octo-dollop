from collections import defaultdict
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.core.db_clients import AsyncSessionLocal
from app.core.config import settings
from loguru import logger

router = APIRouter()


def _resolve_artifact(path_value: str) -> Path:
    artifact_path = Path(path_value)
    if artifact_path.is_absolute():
        return artifact_path
    return Path(__file__).resolve().parents[3] / artifact_path


def _load_json(path_value: str) -> dict:
    path = _resolve_artifact(path_value)
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def _load_ndjson(path_value: str) -> list[dict]:
    path = _resolve_artifact(path_value)
    if not path.exists():
        raise FileNotFoundError(str(path))

    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def _summarize_stage_health(events: list[dict]) -> list[dict]:
    stage_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"OK": 0, "PENDING": 0, "ERROR": 0})
    ordered_stages = [
        "ingesta",
        "clasificacion",
        "auditoria_juridica",
        "firma_inmutable",
        "orden_operativa",
        "cierre",
        "error",
    ]

    for event in events:
        stage = event.get("stage", "error")
        status = event.get("status", "ERROR")
        stage_counts[stage][status] = stage_counts[stage].get(status, 0) + 1

    summary = []
    for stage in ordered_stages:
        counts = stage_counts[stage]
        total = sum(counts.values())
        ok_ratio = round((counts.get("OK", 0) / total) * 100) if total else 0
        pending_ratio = round((counts.get("PENDING", 0) / total) * 100) if total else 0
        status = "healthy"
        if counts.get("ERROR", 0) > 0:
            status = "critical"
        elif counts.get("PENDING", 0) > 0:
            status = "warning"

        summary.append(
            {
                "stage": stage,
                "value": ok_ratio if ok_ratio else pending_ratio,
                "status": status,
                "totals": counts,
            }
        )

    return summary


@router.get("/closed-loop/telemetry")
async def get_closed_loop_telemetry():
    try:
        report = _load_json(settings.CLOSED_LOOP_REPORT_PATH)
        timeline = _load_ndjson(settings.CLOSED_LOOP_EVENTS_PATH)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Artefacto de telemetria no encontrado: {exc}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Artefacto de telemetria invalido: {exc}")

    recent_timeline = sorted(timeline, key=lambda event: event.get("timestamp", ""), reverse=True)[:20]
    stage_summary = _summarize_stage_health(timeline)
    latest_event = recent_timeline[0] if recent_timeline else None

    return {
        "report": report,
        "events": stage_summary,
        "timeline": recent_timeline,
        "summary": {
            "connected": True,
            "alerts": report.get("error_count", 0),
            "maxValue": max((item.get("value", 0) for item in stage_summary), default=0),
            "successRate": report.get("success_rate", 0),
            "throughputRps": report.get("throughput_rps", 0),
            "lastExternalId": latest_event.get("external_id") if latest_event else None,
            "lastStatus": latest_event.get("status") if latest_event else None,
        },
    }

@router.get("/track/{radicado}")
async def track_document(radicado: str):
    """
    Consulta pública de estado - Pasaporte QR V26.5 (Activo). 
    Muestra trazabilidad real de eventos y documentos.
    """
    try:
        async with AsyncSessionLocal() as session:
            # 1. Consultar Registro Base
            query_reg = text("""
                SELECT status, received_at, citizen_name, target_department_id 
                FROM pqrsd_registry WHERE external_id = :rad
            """)
            res_reg = await session.execute(query_reg, {"rad": radicado})
            reg = res_reg.fetchone()
            
            if not reg:
                raise HTTPException(status_code=404, detail="Radicado no encontrado")
            
            # 2. Consultar Trazabilidad (Timeline Real)
            query_trace = text("""
                SELECT estado_nuevo, fecha_change, comentario 
                FROM trazabilidad WHERE external_id = :rad 
                ORDER BY fecha_change ASC
            """)
            # Nota: Corregimos nombre de columna si es necesario (fecha_cambio en init_db)
            query_trace = text("""
                SELECT estado_nuevo, fecha_cambio, comentario 
                FROM trazabilidad WHERE external_id = :rad 
                ORDER BY fecha_cambio ASC
            """)
            res_trace = await session.execute(query_trace, {"rad": radicado})
            traces = res_trace.fetchall()
            
            # 3. Consultar Documentos
            query_docs = text("SELECT gcs_uri, tipo_documento FROM evidencias_bucket WHERE external_id = :rad")
            res_docs = await session.execute(query_docs, {"rad": radicado})
            docs = res_docs.fetchall()

            # 4. Consultar Sello Ledger
            query_ledger = text("SELECT current_hash, transaction_id FROM audit_ledger WHERE registry_id = :rad ORDER BY created_at DESC LIMIT 1")
            res_ledger = await session.execute(query_ledger, {"rad": radicado})
            ledger = res_ledger.fetchone()

            # --- MAPEO DE ESTADOS ---
            status_map = {
                "RECIBIDO": ("📥 Recibido y Sellado", "Tu solicitud ha sido registrada bajo la gravedad de juramento."),
                "ASIGNADO": ("🏢 En Revisión", "El caso ya está en el escritorio digital de la dependencia."),
                "RESOLVED": ("✅ Resuelto", "La Alcaldía ha emitido una resolución oficial.")
            }
            ui_label, ui_message = status_map.get(reg[0], ("⚙️ En Trámite", "Estamos procesando su solicitud."))

            import datetime
            return {
                "radicado": radicado,
                "peticionario": reg[2],
                "pasaporte_digital": {
                    "estado_actual": ui_label,
                    "mensaje": ui_message,
                    "timeline_real": [
                        {"estado": t[0], "fecha": t[1].isoformat(), "nota": t[2]} for t in traces
                    ],
                    "documentos_expediente": [
                        {"tipo": d[1], "uri": d[0]} for d in docs
                    ]
                },
                "seguridad_forense": {
                    "hash_integridad": ledger[0] if ledger else "PENDIENTE",
                    "transaction_id": ledger[1] if ledger else "LOCAL_ONLY",
                    "infraestructura": "GCP Immutable Storage + KMS"
                }
            }
    except Exception as e:
        logger.error(f"Error en tracking V26.5: {str(e)}")
        raise HTTPException(status_code=500, detail="Fallo en motor de trazabilidad")
