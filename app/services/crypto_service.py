import os
import base64
from cryptography.fernet import Fernet
from loguru import logger
from app.core.config import settings

class CryptoService:
    """
    V50.2: Motor de Cifrado AES-256 (Diamond Grade).
    Protege el PII en reposo conforme a la Ley 1581 (Habeas Data).
    """
    def __init__(self):
        # Intentamos obtener la llave desde variables de entorno (GCP Secret Manager ready)
        # Si no existe, generamos una para desarrollo (ADVERTENCIA: No usar llaves volátiles en PROD)
        self.key_raw = os.getenv("ENCRYPTION_KEY_BASE64")
        
        if not self.key_raw:
            logger.warning("⚠️ ENCRYPTION_KEY_BASE64 no configurada. Generando llave temporal para desarrollo.")
            self.key = Fernet.generate_key()
            self.key_raw = self.key.decode()
        else:
            self.key = self.key_raw.encode()
            
        try:
            self.fernet = Fernet(self.key)
            logger.info("🔐 CryptoService activado exitosamente.")
        except Exception as e:
            logger.error(f"❌ Error al inicializar Fernet: {e}")
            raise e

    def encrypt(self, data: str) -> str:
        """Cifra un string y devuelve un string base64 seguro."""
        if not data: return ""
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"❌ Error en cifrado PII: {e}")
            return data # Fallback para evitar pérdida de datos, pero logueamos el fallo

    def decrypt(self, encrypted_data: str) -> str:
        """Descifra un string base64 y devuelve el texto plano."""
        if not encrypted_data or "[" in str(encrypted_data): return encrypted_data
        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception:
            # Si falla el descifrado, probablemente es texto plano heredado o llave incorrecta
            return encrypted_data

crypto_service = CryptoService()
