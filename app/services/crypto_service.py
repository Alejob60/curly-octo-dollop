import base64
from cryptography.fernet import Fernet
from loguru import logger
from app.core.config import settings

class CryptoService:
    """
    V1.0: Servicio de Cifrado Simétrico para PII.
    Utiliza Fernet (AES-128 en modo CBC con HMAC-SHA256).
    """
    def __init__(self):
        # Intentar obtener la llave desde settings o usar una fija para la demo
        raw_key = settings.DATABASE_ENCRYPTION_KEY or "fallback-secret-key-32-chars-long!!"
        
        # Fernet requiere una llave de 32 bytes codificada en base64
        # Si la llave no tiene 32 bytes, la ajustamos con hash
        import hashlib
        key_32 = hashlib.sha256(raw_key.encode()).digest()
        self.key = base64.urlsafe_b64encode(key_32)
        self.fernet = Fernet(self.key)
        logger.info("🔐 CryptoService: Motor de cifrado inicializado.")

    def encrypt(self, plain_text: str) -> str:
        if not plain_text: return ""
        try:
            return self.fernet.encrypt(plain_text.encode()).decode()
        except Exception as e:
            logger.error(f"❌ Error al cifrar: {e}")
            return plain_text

    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text: return ""
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except Exception as e:
            logger.error(f"❌ Error al descifrar: {e}")
            return encrypted_text

crypto_service = CryptoService()
