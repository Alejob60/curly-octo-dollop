import json
import os
from datetime import datetime, timedelta
from google.cloud import storage
from app.core.config import settings
from loguru import logger

class GCPStorageOrchestrator:
    """
    V47.0: Orquestador de Almacenamiento GCP-NATIVE.
    Gestiona el ciclo de vida de los archivos en GCS (Hot y Cold Storage).
    """
    def __init__(self):
        self.bucket_name = settings.GCS_BUCKET_NAME
        try:
            self.storage_client = storage.Client(project=settings.GCP_PROJECT_ID)
            self.bucket = self.storage_client.bucket(self.bucket_name)
            logger.info(f"🏛️ GCS Storage Orchestrator inicializado en bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Error conectando a GCP Storage: {e}")
            self.storage_client = None
            self.bucket = None

    def upload_artifact(self, content, radicado_id: str, folder: str, filename: str) -> str:
        """Sube un artefacto oficial al búnker digital de GCS."""
        if not self.bucket: return f"offline/{radicado_id}/{folder}/{filename}"
        try:
            blob_path = f"{radicado_id}/{folder}/{filename}"
            blob = self.bucket.blob(blob_path)
            
            if isinstance(content, dict):
                payload = json.dumps(content, indent=2).encode("utf-8")
                ctype = "application/json"
            elif isinstance(content, str):
                payload = content.encode("utf-8")
                ctype = "text/plain"
            else:
                payload = content
                ctype = "application/octet-stream"
            
            blob.upload_from_string(payload, content_type=ctype)
            logger.info(f"✅ Artefacto subido a GCS: {blob_path}")
            return blob_path
        except Exception as e:
            logger.error(f"Error subida GCS: {e}")
            return None

    def get_signed_url(self, blob_path: str, expiry_hours: int = 24) -> str:
        """Genera una URL firmada de GCP para acceso seguro temporal."""
        if not self.bucket: return f"https://storage.googleapis.com/{blob_path}"
        try:
            blob = self.bucket.blob(blob_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=expiry_hours),
                method="GET"
            )
            return url
        except Exception as e:
            logger.warning(f"Fallo firma GCS: {e}")
            return f"https://storage.googleapis.com/{self.bucket_name}/{blob_path}"

    def move_to_cold_storage(self, radicado_id: str):
        """Mueve todo el expediente a la clase ARCHIVE (Retención 20 años)."""
        if not self.bucket: return
        try:
            blobs = self.storage_client.list_blobs(self.bucket_name, prefix=f"{radicado_id}/")
            for blob in blobs:
                # Cambio de clase de almacenamiento para ahorro de costos a largo plazo
                blob.update_storage_class("ARCHIVE")
                logger.info(f"❄️ Expediente {radicado_id} movido a Bóveda Fría GCP.")
            return True
        except Exception as e:
            logger.error(f"Error archivado GCS: {e}")
            return False

gcp_storage_orchestrator = GCPStorageOrchestrator()
