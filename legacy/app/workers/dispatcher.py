import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from google.cloud import pubsub_v1
except ImportError:
    pubsub_v1 = None
from loguru import logger

from app.core.config import settings
from app.core.db_clients import mongo_db


class HistoricalIngestionDispatcher:
    def __init__(self):
        self.project_id = settings.GCP_PUBSUB_PROJECT_ID
        self.topic_name = settings.GCP_PUBSUB_TOPIC
        self._publisher = None
        self._topic_path = None

        if not self.project_id:
            logger.warning("Dispatcher sin GCP_PUBSUB_PROJECT_ID; usara cola Mongo local.")
            return

        if pubsub_v1 is None:
            logger.warning("google-cloud-pubsub no esta disponible; se usara cola Mongo local.")
            return

        # Check for ADC or specific credentials
        adc_path = os.path.join(os.environ.get('APPDATA', ''), 'gcloud', 'application_default_credentials.json')
        has_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.path.exists(adc_path) or os.getenv("PUBSUB_EMULATOR_HOST")

        if not has_creds:
            logger.warning("Sin credenciales detectadas para Pub/Sub; se usara cola Mongo local.")
            return

        try:
            self._publisher = pubsub_v1.PublisherClient()
            self._topic_path = self._publisher.topic_path(self.project_id, self.topic_name)
            logger.info(f"✅ Pub/Sub Dispatcher conectado a tópico: {self.topic_name}")
        except Exception as exc:
            logger.warning(f"No fue posible iniciar Pub/Sub publisher: {exc}")
            self._publisher = None
            self._topic_path = None

    async def publish_pdf_jobs(self, jobs: List[Dict[str, Any]]) -> Dict[str, int]:
        published = 0
        queued = 0

        for job in jobs:
            success = await self.publish_single_job(job)
            if success == "pubsub":
                published += 1
            else:
                queued += 1

        return {
            "pubsub_published": published,
            "mongo_queued": queued,
        }

    async def publish_single_job(self, payload: Dict[str, Any]) -> str:
        payload = {
            **payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self._publisher and self._topic_path:
            try:
                message_bytes = json.dumps(payload, ensure_ascii=True).encode("utf-8")
                future = self._publisher.publish(self._topic_path, message_bytes)
                future.result(timeout=10)
                return "pubsub"
            except Exception as exc:
                logger.warning(f"Fallo publicacion Pub/Sub; usando cola Mongo: {exc}")

        await mongo_db.ingestion_queue.update_one(
            {"idempotency_key": payload.get("idempotency_key")},
            {
                "$set": {
                    "payload": payload,
                    "status": "pending",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                "$setOnInsert": {
                    "created_at": payload["created_at"],
                },
            },
            upsert=True,
        )
        return "mongo"

    async def get_dispatcher_health(self) -> Dict[str, Any]:
        return {
            "pubsub_enabled": bool(self._publisher and self._topic_path),
            "project_id": self.project_id,
            "topic": self.topic_name,
        }


historical_dispatcher = HistoricalIngestionDispatcher()
