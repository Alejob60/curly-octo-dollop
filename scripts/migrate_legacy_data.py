import httpx
import asyncio
import json
import csv
import sys
import os
from loguru import logger

# Configuración
BASE_URL = "http://localhost:8000/api/v1/pqrs"
BATCH_SIZE = 100 # Cantidad de registros por lote de envío

async def migrate_json(file_path: str):
    """Lee un archivo JSON con registros legacy y los inyecta en el motor."""
    if not os.path.exists(file_path):
        logger.error(f"❌ Archivo no encontrado: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            logger.error("❌ El formato del JSON debe ser una lista de objetos.")
            return

        logger.info(f"📊 Iniciando migración de {len(data)} registros...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            count = 0
            for item in data:
                try:
                    # Enviar al endpoint unificado
                    res = await client.post(
                        f"{BASE_URL}/submit",
                        json=item,
                        headers={"X-Source": "migration"}
                    )
                    
                    if res.status_code == 202:
                        count += 1
                        if count % BATCH_SIZE == 0:
                            logger.info(f"✅ Inyectados {count} registros...")
                    else:
                        logger.warning(f"⚠️ Fallo en registro: {res.text}")
                except Exception as e:
                    logger.error(f"🔥 Error en envío: {e}")
            
        logger.success(f"🏁 Migración completada. Total exitosos: {count}")

    except Exception as e:
        logger.error(f"💥 Error fatal en migración: {e}")

async def migrate_csv(file_path: str):
    """Lee un archivo CSV y lo migra."""
    # Implementación similar para CSV si se requiere
    pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/migrate_legacy_data.py <path_to_json>")
        sys.exit(1)
        
    path = sys.argv[1]
    asyncio.run(migrate_json(path))
