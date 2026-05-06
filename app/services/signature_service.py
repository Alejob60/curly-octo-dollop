import hashlib
import hmac
from loguru import logger
from app.core.config import settings

class SignatureService:
    def __init__(self):
        # En producción, esto se recuperaría de Cloud KMS o Secret Manager
        self._master_secret = settings.JWT_SECRET 

    def generate_electronic_signature(self, document_content: str, funcionario_id: str) -> str:
        """
        SEC-03: Genera una Firma Electrónica Avanzada (SHA-256).
        Vincula el contenido del documento con la identidad del funcionario.
        """
        try:
            # Creamos un payload único: Documento + Funcionario + Secreto Maestro
            payload = f"{document_content}|{funcionario_id}|{self._master_secret}"
            
            # Generamos el Hash SHA-256
            signature = hashlib.sha256(payload.encode()).hexdigest()
            
            logger.info(f"Firma electrónica generada para funcionario {funcionario_id}")
            return signature
        except Exception as e:
            logger.error(f"Error generando firma electrónica: {e}")
            return None

    def verify_signature(self, document_content: str, funcionario_id: str, signature_to_verify: str) -> bool:
        """
        Verifica si el documento ha sido alterado comparando el Hash.
        """
        expected_signature = self.generate_electronic_signature(document_content, funcionario_id)
        return hmac.compare_digest(expected_signature, signature_to_verify)

signature_service = SignatureService()
