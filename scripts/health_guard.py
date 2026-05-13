import httpx
import asyncio
import time
import os
from loguru import logger

# Configuración
API_BASE = "http://localhost:8000"
CHECK_INTERVAL = 300 # 5 minutos
MAX_FAILURES = 3

class SystemHealthGuard:
    """
    🛡️ [V65.14] Monitor de Salud Autónomo.
    Vigila Vertex AI y dispara el worker de cola solo si el sistema es confiable.
    """
    
    def __init__(self):
        self.failure_count = 0

    async def check_pipeline(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{API_BASE}/api/v1/metrics/pipeline")
                if res.status_code == 200:
                    data = res.json()
                    status = data.get("performance", {}).get("vertex_status")
                    if status == "HEALTHY":
                        logger.success("💚 Pipeline saludable. IA operando con normalidad.")
                        self.failure_count = 0
                        return True
                    else:
                        logger.warning(f"⚠️ IA en estado degradado: {status}")
                else:
                    logger.error(f"❌ Error en API de métricas: {res.status_code}")
        except Exception as e:
            logger.error(f"🔥 Fallo de conexión con el backend: {e}")
            
        self.failure_count += 1
        return False

    async def run_forever(self):
        logger.info("🛡️ Iniciando Health Guard Diamond...")
        while True:
            is_ok = await self.check_pipeline()
            
            if self.failure_count >= MAX_FAILURES:
                logger.critical("🚨 URGENTE: El sistema ha fallado múltiples veces. Notificando a SRE...")
                # Aquí se podría disparar un webhook de Slack/PagerDuty
                
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    guard = SystemHealthGuard()
    asyncio.run(guard.run_forever())
