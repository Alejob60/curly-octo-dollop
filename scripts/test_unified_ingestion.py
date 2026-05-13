import httpx
import asyncio
import json
import time
from loguru import logger

BASE_URL = "http://localhost:8088/api/v1/pqrs"

async def test_unified_flow():
    logger.info("🧪 Iniciando Test de Ingesta Unificada (V65.13)")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Enviar solicitud vía submit (API Mode)
        payload = {
            "asunto": "Test de Ingesta Unificada",
            "descripcion": "Solicito información técnica sobre el protocolo de seguridad de la Bóveda Digital para la Secretaría de Salud.",
            "identificacion": "CC-987654321",
            "email": "tester@cali.gov.co",
            "source": "api"
        }
        
        logger.info("1. 📥 Enviando solicitud al endpoint /submit...")
        res = await client.post(f"{BASE_URL}/submit", json=payload)
        
        if res.status_code != 202:
            logger.error(f"❌ Fallo en submit: {res.text}")
            return
            
        data = res.json()
        idem_key = data["idempotency_key"]
        logger.success(f"✅ Solicitud aceptada. Idempotency Key: {idem_key}")
        
        # 2. Monitorear estadísticas de la cola
        logger.info("2. ⏳ Esperando a que el worker procese la tarea...")
        for i in range(15):
            await asyncio.sleep(3)
            stats_res = await client.get(f"{BASE_URL}/queue/stats")
            stats = stats_res.json()
            logger.info(f"📊 Stats: {stats}")
            
            if stats.get("completed", 0) > 0:
                logger.success("🏁 ¡Tarea completada por el worker!")
                break
            if stats.get("failed_dlq", 0) > 0:
                logger.error("💀 La tarea falló y fue movida a la DLQ.")
                break
        else:
            logger.warning("🕒 Timeout esperando procesamiento.")

if __name__ == "__main__":
    asyncio.run(test_unified_flow())
