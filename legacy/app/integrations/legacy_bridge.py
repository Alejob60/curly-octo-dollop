import httpx
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger
from app.core.config import settings
import time

class CircuitBreaker:
    """
    V61.0: Cortocircuito para protección de APIs Legacy.
    Evita saturar sistemas lentos (Orfeo/SAP) si detecta fallos masivos.
    """
    def __init__(self, limit: int = 10, window: int = 60):
        self.limit = limit
        self.window = window
        self.failures = []

    def can_execute(self) -> bool:
        now = time.time()
        # Limpiamos fallos fuera de la ventana de tiempo
        self.failures = [f for f in self.failures if now - f < self.window]
        return len(self.failures) < self.limit

    def record_failure(self):
        self.failures.append(time.time())

class LegacyBridgeClient:
    """
    Base para clientes de interoperabilidad GovTech.
    Incluye Retry Exponencial y Circuit Breaker.
    """
    def __init__(self, base_url: str, name: str):
        self.base_url = base_url
        self.name = name
        self.cb = CircuitBreaker()
        self.headers = {"Authorization": f"Bearer {settings.LEGACY_BRIDGE_TOKEN}"}

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        if not self.cb.can_execute():
            logger.error(f"🛑 [CIRCUIT_BREAKER] {self.name} bloqueado temporalmente.")
            return None

        # Lógica de Retry Exponencial
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=settings.LEGACY_API_TIMEOUT) as client:
                    response = await client.request(method, f"{self.base_url}{endpoint}", headers=self.headers, **kwargs)
                    response.raise_for_status()
                    return response.json()
            except Exception as e:
                wait_time = (2 ** attempt)
                logger.warning(f"⚠️ [{self.name}] Intento {attempt+1} falló: {e}. Reintentando en {wait_time}s...")
                await asyncio.sleep(wait_time)
        
        self.cb.record_failure()
        return None

class OrfeoBridge(LegacyBridgeClient):
    """
    V61.1: Adaptador para Orfeo NG.
    """
    def __init__(self):
        super().__init__(settings.ORFEO_BRIDGE_URL, "ORFEO")

    async def get_pqrs_batch(self, limit: int = 100, after_radicado: Optional[str] = None) -> Dict:
        """Extracción cursor-based para backlog masivo."""
        params = {"limit": limit}
        if after_radicado: params["after_radicado"] = after_radicado
        return await self._request("GET", "/pqrs/batch", params=params)

    async def push_response(self, radicado: str, resolution_pdf_b64: str, kms_hash: str) -> bool:
        """Push-back de respuesta aprobada por humano."""
        res = await self._request("POST", f"/pqrs/{radicado}/response", json={
            "resolution_pdf": resolution_pdf_b64,
            "kms_hash": kms_hash
        })
        return res is not None

class SAULBridge(LegacyBridgeClient):
    """
    V61.1: Adaptador para SAUL (Catastro).
    """
    def __init__(self):
        super().__init__(settings.SAUL_BRIDGE_URL, "SAUL")

    async def get_predio(self, matricula: str) -> Dict:
        return await self._request("GET", f"/predios/matricula/{matricula}")

class SAPBridge(LegacyBridgeClient):
    """
    V61.1: Adaptador para SAP ECC (Financiero).
    """
    def __init__(self):
        super().__init__(settings.SAP_BRIDGE_URL, "SAP")

    async def get_citizen_payments(self, documento: str) -> List:
        return await self._request("GET", f"/pagos/ciudadano/{documento}")

# Singletons para interoperabilidad global
orfeo_bridge = OrfeoBridge()
saul_bridge = SAULBridge()
sap_bridge = SAPBridge()
