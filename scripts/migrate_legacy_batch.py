import httpx
import asyncio
import json
import os
import sys
import hashlib
from loguru import logger
from typing import List, Dict

# Configuración Diamond V65.14
API_URL = "http://localhost:8000/api/v1/pqrs/submit"
STATS_URL = "http://localhost:8000/api/v1/pqrs/queue/stats"
CONCURRENCY_LIMIT = 50 # Cuántas peticiones HTTP simultáneas de inyección
BATCH_LOG_SIZE = 500

async def migrate_batch(data: List[Dict]):
    """
    💎 [V65.14] Inyector Masivo Idempotente.
    Procesa lotes de datos legacy hacia el pipeline Diamond.
    """
    logger.info(f"🚀 Iniciando migración masiva de {len(data)} registros...")
    
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        tasks = []
        for i, item in enumerate(data):
            # Generar idempotency key si no la tiene para evitar duplicados
            if "idempotency_key" not in item:
                seed = f"{item.get('asunto', 'MIG')}-{item.get('identificacion', i)}"
                item["idempotency_key"] = hashlib.md5(seed.encode()).hexdigest()
            
            tasks.append(_inject_task(client, item, semaphore, i))
            
        results = await asyncio.gather(*tasks)
        
        success = sum(1 for r in results if r)
        logger.success(f"🏁 Carga de Batch completada: {success}/{len(data)} registros inyectados.")
        
        # Verificar estado de la cola
        res_stats = await client.get(STATS_URL)
        logger.info(f"📊 Estado actual de la cola en el servidor: {res_stats.text}")

async def _inject_task(client, payload, sem, index) -> bool:
    async with sem:
        try:
            res = await client.post(
                API_URL, 
                json=payload,
                headers={"X-Source": "migration", "X-Priority": "NORMAL"}
            )
            if res.status_code == 202:
                if index % BATCH_LOG_SIZE == 0:
                    logger.debug(f"✅ Inyectado índice {index}")
                return True
            elif res.status_code == 200 and res.json().get("status") == "DUPLICATE":
                return True # Contamos duplicados como éxito de "ya está ahí"
            else:
                logger.error(f"❌ Error en índice {index}: {res.text}")
                return False
        except Exception as e:
            logger.error(f"🔥 Fallo crítico en inyección {index}: {e}")
            return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/migrate_legacy_batch.py <archivo_legacy.json>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        logger.error("Archivo no encontrado.")
        sys.exit(1)
        
    with open(file_path, 'r', encoding='utf-8') as f:
        legacy_data = json.load(f)
        
    asyncio.run(migrate_batch(legacy_data))
