import httpx
from loguru import logger
from fastapi import HTTPException, status
from app.core.config import settings

REALCULTURE_BASE_URL = "https://realculture-backend-348740051349.us-central1.run.app/api"

class RealCultureAuthClient:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=REALCULTURE_BASE_URL, timeout=30.0)

    async def login(self, email: str, password: str) -> dict:
        """
        AUTH-EXT: Autentica vía RealCulture AI Backend.
        """
        try:
            response = await self.client.post("/auth/login", json={
                "email": email,
                "password": password
            })
            if response.status_code == 200:
                logger.success(f"Login exitoso en RealCulture: {email}")
                return response.json()
            else:
                logger.warning(f"Fallo login RealCulture: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Credenciales inválidas en RealCulture")
        except Exception as e:
            logger.error(f"Error de conexión con RealCulture Auth: {e}")
            raise HTTPException(status_code=503, detail="Servicio de autenticación no disponible")

    async def register(self, name: str, email: str, password: str, tenant_id: str) -> dict:
        """
        AUTH-EXT: Registra nuevo usuario en RealCulture AI Backend.
        """
        try:
            response = await self.client.post("/auth/register", json={
                "name": name,
                "email": email,
                "password": password,
                "tenantId": tenant_id
            })
            if response.status_code == 201:
                logger.success(f"Registro exitoso en RealCulture: {email}")
                return response.json()
            else:
                logger.warning(f"Fallo registro RealCulture: {response.text}")
                raise HTTPException(status_code=response.status_code, detail=response.json().get("message", "Error en registro"))
        except Exception as e:
            logger.error(f"Error registrando en RealCulture: {e}")
            raise HTTPException(status_code=503, detail="Servicio de registro no disponible")

realculture_auth = RealCultureAuthClient()
