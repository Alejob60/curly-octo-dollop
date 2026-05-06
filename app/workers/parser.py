import io
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pdfplumber
from google.cloud import storage
from loguru import logger
from pymongo import UpdateOne

from app.core.config import settings
from app.core.db_clients import mongo_db
from app.services.vectorizer import historical_vectorizer


RESPONSIBLE_MAP = {
    "infraestructura": "4151010",
    "movilidad": "4152000",
    "hacienda": "4131000",
    "juridica": "4111000",
    "alumbrado": "4151010",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HistoricalPdfParserWorker:
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.raw_bucket_name = settings.GCP_RAW_PDF_BUCKET
        self.batch_size = settings.INGEST_BATCH_SIZE
        self.vectorize_on_insert = settings.INGEST_VECTORIZE_ON_INSERT
        self._storage_client = None

        try:
            if self.project_id:
                self._storage_client = storage.Client(project=self.project_id)
            else:
                self._storage_client = storage.Client()
        except Exception as exc:
            logger.warning(f"No fue posible iniciar cliente GCS en parser: {exc}")
            self._storage_client = None

    async def process_queue_once(self, max_jobs: int = 10) -> Dict[str, int]:
        jobs = await mongo_db.ingestion_queue.find({"status": "pending"}).limit(max_jobs).to_list(length=max_jobs)
        processed = 0
        failed = 0

        for job in jobs:
            payload = job.get("payload") or {}
            try:
                await self.process_pubsub_payload(payload)
                await mongo_db.ingestion_queue.update_one(
                    {"_id": job["_id"]},
                    {"$set": {"status": "processed", "updated_at": _utc_now_iso()}},
                )
                processed += 1
            except Exception as exc:
                await mongo_db.ingestion_queue.update_one(
                    {"_id": job["_id"]},
                    {
                        "$set": {
                            "status": "failed",
                            "error": str(exc),
                            "updated_at": _utc_now_iso(),
                        }
                    },
                )
                failed += 1
                logger.error(f"Fallo procesando job historico: {exc}")

        return {"processed": processed, "failed": failed}

    async def process_pubsub_payload(self, payload: Dict[str, Any]) -> Dict[str, int]:
        bucket_name = payload.get("bucket_name") or self.raw_bucket_name
        blob_name = payload.get("blob_name")
        if not bucket_name or not blob_name:
            raise ValueError("Payload invalido: falta bucket_name o blob_name")

        pdf_bytes = self._download_pdf_bytes(bucket_name, blob_name)
        rows = self._extract_rows(pdf_bytes)
        if not rows:
            return {"inserted": 0, "updated": 0}

        operations = []
        now_iso = _utc_now_iso()
        for row in rows:
            filter_document = {"radicado": row["radicado"]}
            update_document = {
                "$set": {
                    **row,
                    "source_blob": blob_name,
                    "updated_at": now_iso,
                },
                "$setOnInsert": {
                    "created_at": now_iso,
                },
            }
            operations.append(UpdateOne(filter_document, update_document, upsert=True))

        bulk_result = await mongo_db.pqrsd_history.bulk_write(operations, ordered=False)
        inserted = bulk_result.upserted_count
        updated = bulk_result.modified_count

        await mongo_db.ingest_pipeline_metrics.update_one(
            {"_id": "pqrs_historical"},
            {
                "$set": {
                    "last_blob": blob_name,
                    "last_run_at": now_iso,
                    "last_inserted": inserted,
                    "last_updated": updated,
                },
                "$inc": {
                    "total_inserted": inserted,
                    "total_updated": updated,
                },
            },
            upsert=True,
        )

        if self.vectorize_on_insert:
            await historical_vectorizer.vectorize_pending(limit=min(self.batch_size, 200))

        return {"inserted": inserted, "updated": updated}

    def _download_pdf_bytes(self, bucket_name: str, blob_name: str) -> bytes:
        if not self._storage_client:
            raise RuntimeError("GCS client no disponible en parser")

        bucket = self._storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        return blob.download_as_bytes()

    def _extract_rows(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if not table or len(table) < 2:
                    continue

                headers = [self._normalize_header(col) for col in table[0]]
                for raw_row in table[1:]:
                    parsed = self._parse_row(headers, raw_row)
                    if parsed:
                        rows.append(parsed)

        return rows

    def _parse_row(self, headers: List[str], row: List[Optional[str]]) -> Optional[Dict[str, Any]]:
        values = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}

        radicado = self._clean_text(values.get("radicacion") or values.get("radicado") or "")
        if not radicado:
            return None

        responsable = self._clean_text(values.get("responsable") or "")
        asunto = self._clean_text(values.get("asunto") or "")

        fecha_radicacion = self._normalize_date(values.get("fecha_radicacion") or values.get("fecha_radicacion_"))
        fecha_respuesta = self._normalize_date(values.get("fecha_respuesta"))
        fecha_vencimiento = self._normalize_date(values.get("fecha_vencimiento"))

        response_days = None
        if fecha_radicacion and fecha_respuesta:
            try:
                start = datetime.fromisoformat(fecha_radicacion)
                end = datetime.fromisoformat(fecha_respuesta)
                response_days = max(0, (end - start).days)
            except Exception:
                response_days = None

        return {
            "radicado": radicado,
            "fecha_radicacion": fecha_radicacion,
            "responsable": responsable,
            "responsable_id": self._map_responsible_id(responsable),
            "tipo": self._clean_text(values.get("tipo") or ""),
            "asunto": asunto,
            "respuesta": self._clean_text(values.get("respuesta") or ""),
            "fecha_respuesta": fecha_respuesta,
            "fecha_vencimiento": fecha_vencimiento,
            "response_days": response_days,
        }

    @staticmethod
    def _normalize_header(value: Optional[str]) -> str:
        value = (value or "").strip().lower()
        value = re.sub(r"\s+", "_", value)
        value = value.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        return value

    @staticmethod
    def _clean_text(value: Optional[str]) -> str:
        value = (value or "").replace("\n", " ").strip()
        return re.sub(r"\s+", " ", value)

    @staticmethod
    def _normalize_date(raw_value: Optional[str]) -> Optional[str]:
        value = (raw_value or "").strip()
        if not value:
            return None

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue

        return None

    @staticmethod
    def _map_responsible_id(responsable: str) -> str:
        text_value = responsable.lower()
        for key, value in RESPONSIBLE_MAP.items():
            if key in text_value:
                return value
        return "0000000"


historical_pdf_parser = HistoricalPdfParserWorker()
