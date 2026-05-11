import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from google.cloud import storage
from loguru import logger

from app.core.config import settings


class GCPImmutableStorageService:
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.tenant_prefix = settings.GCP_TENANT_PREFIX
        self.bucket_name = settings.GCP_IMMUTABLE_BUCKET or settings.GCS_BUCKET_NAME
        self.retention_days = settings.GCP_WORM_RETENTION_DAYS
        
        # SEC-01: Configuración de Llave KMS (Soberanía de Datos)
        self.kms_key_name = getattr(settings, "GCP_KMS_KEY_NAME", None)

        self.client = None
        self.bucket = None

        if not self.bucket_name:
            logger.warning("GCP immutable bucket is not configured.")
            return

        try:
            self.client = storage.Client(project=self.project_id or None)
            self.bucket = self.client.bucket(self.bucket_name)
            logger.info(f"GCP immutable storage initialized: {self.bucket_name}")
            
            if self.kms_key_name:
                logger.info(f"🛡️ Cifrado KMS Activado: Usando llave maestra para blindaje en reposo.")

            self._ensure_bucket_retention_policy()
        except Exception as e:
            logger.error(f"Error initializing GCP immutable storage: {str(e)}")
            self.client = None
            self.bucket = None

    def _ensure_bucket_retention_policy(self):
        if not self.bucket:
            return

        # ARC-01: Retención legal de 20 años (7300 días)
        retention_days = 7300 
        retention_seconds = retention_days * 24 * 60 * 60
        
        try:
            current = int(self.bucket.retention_period or 0)
            if current < retention_seconds:
                self.bucket.retention_period = retention_seconds
                self.bucket.patch()
                logger.info(f"🏛️ Política de Retención Legal activada: 20 años ({retention_days} días).")
        except Exception as e:
            logger.warning(f"No se pudo actualizar la política de retención del bucket: {str(e)}")

    def move_to_long_term_archive(self, object_path: str):
        """
        ARC-01: Mueve el documento a la clase ARCHIVE y establece el bloqueo definitivo.
        Se ejecuta al cerrar legalmente el radicado.
        """
        if not self.bucket or not object_path or not object_path.startswith("gs://"):
            return

        try:
            path_relativo = object_path.replace(f"gs://{self.bucket_name}/", "")
            blob = self.bucket.blob(path_relativo)
            
            # 1. Cambiar a clase ARCHIVE (Soberanía Documental)
            blob.update_storage_class("ARCHIVE")
            
            # 2. Establecer bloqueo por evento (Ley de Archivo)
            blob.event_based_hold = True
            blob.temporary_hold = False
            blob.patch()
            
            logger.success(f"📦 Documento archivado por 20 años: {path_relativo}")
            return True
        except Exception as e:
            logger.error(f"Error en archivado a largo plazo: {e}")
            return False

    def upload_to_immutable_bucket(
        self,
        payload: Dict,
        external_id: str,
        action: str,
        signature: Optional[str] = None,
        digest_sha256: Optional[str] = None,
        is_binary: bool = False,
        content: Optional[bytes] = None
    ) -> str:
        if not self.bucket:
            return f"simulated://{self.tenant_prefix}/{external_id}/{action}.json"

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        ext = "pdf" if is_binary else "json"
        object_path = (
            f"{self.tenant_prefix}/vault/{external_id}/{timestamp}_{action.lower()}.{ext}"
        )

        try:
            # SEC-01: Aplicar cifrado KMS si está disponible
            blob = self.bucket.blob(object_path, kms_key_name=self.kms_key_name)
            
            blob.metadata = {
                "tenant_prefix": self.tenant_prefix,
                "external_id": external_id,
                "action": action,
                "digest_sha256": digest_sha256 or "",
                "encryption": "GCP_KMS_CMEK" if self.kms_key_name else "GCP_DEFAULT"
            }

            if is_binary and content:
                blob.upload_from_string(content, content_type="application/pdf")
            else:
                document = {
                    "external_id": external_id, "action": action, 
                    "tenant_prefix": self.tenant_prefix, "generated_at_utc": timestamp,
                    "digest_sha256": digest_sha256, "signature": signature, "payload": payload,
                }
                blob.upload_from_string(
                    json.dumps(document, ensure_ascii=True, sort_keys=True, indent=2),
                    content_type="application/json",
                )

            # ARC-01: Asegurar inmutabilidad inmediata
            blob.temporary_hold = True
            blob.patch()

            return f"gs://{self.bucket_name}/{object_path}"
        except Exception as e:
            logger.error(f"Failed to upload immutable object to GCP: {str(e)}")
            return f"failed://{self.tenant_prefix}/{external_id}/{action}"


immutable_storage_service = GCPImmutableStorageService()
