import base64
import hashlib
import hmac
from typing import Dict, Optional
from loguru import logger
from app.core.config import settings

class GCPSignerService:
    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.location = settings.GCP_KMS_LOCATION
        self.keyring = settings.GCP_KMS_KEYRING
        self.key = settings.GCP_KMS_KEY
        self.tenant_prefix = settings.GCP_TENANT_PREFIX
        self.master_key = settings.DATABASE_ENCRYPTION_KEY or "fallback-secret-key-32-chars-long!!"

        self.client = None
        self._digest_cls = None
        if self.project_id and self.location and self.keyring and self.key:
            try:
                from google.cloud import kms_v1
                from google.cloud.kms_v1.types import Digest

                self.client = kms_v1.KeyManagementServiceClient()
                self._digest_cls = Digest
                logger.info("✅ GCP KMS Signer: Cliente inicializado.")
            except Exception as e:
                logger.warning(f"⚠️ KMS Client init failed: {str(e)}. Usando Firma Local.")
                self.client = None

    def _crypto_key_version_path(self) -> Optional[str]:
        if not self.client: return None
        return self.client.crypto_key_version_path(
            self.project_id, self.location, self.keyring, self.key, "1"
        )

    def _generate_local_signature(self, digest_hex: str) -> str:
        """Genera una firma HMAC-SHA256 de respaldo si KMS no está disponible."""
        signature = hmac.new(
            self.master_key.encode(),
            digest_hex.encode(),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode("ascii")

    def sign_digest_sha256(self, digest_hex: str) -> Dict[str, Optional[str]]:
        """
        Firma un digest usando GCP KMS. 
        Si KMS falla (404 o configuración), aplica Firma Resiliente Local.
        """
        key_version_name = self._crypto_key_version_path()
        
        if self.client and key_version_name:
            try:
                digest_bytes = bytes.fromhex(digest_hex)
                response = self.client.asymmetric_sign(
                    request={
                        "name": key_version_name,
                        "digest": self._digest_cls(sha256=digest_bytes),
                    }
                )
                signature_b64 = base64.b64encode(response.signature).decode("ascii")
                return {
                    "provider": "gcp-kms",
                    "key_version": key_version_name,
                    "signature_b64": signature_b64,
                    "tenant_prefix": self.tenant_prefix,
                }
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    logger.warning(f"🚀 [RESILIENCIA] KMS Key no encontrada (404). Activando Firma Local de Emergencia.")
                else:
                    logger.error(f"❌ KMS Signing Error: {str(e)}. Aplicando Fallback.")
        
        # --- FALLBACK: FIRMA LOCAL RESILIENTE ---
        local_sig = self._generate_local_signature(digest_hex)
        return {
            "provider": "local-resilient-hmac",
            "key_version": "LOCAL_V1_EMERGENCY",
            "signature_b64": local_sig,
            "tenant_prefix": self.tenant_prefix,
        }

signer_service = GCPSignerService()
