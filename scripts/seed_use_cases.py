import asyncio
import os
import sys

# Asegurar que el sistema reconozca el módulo app
sys.path.append(os.getcwd())

from app.services.use_case_service import use_case_service
from loguru import logger

async def main():
    logger.info("🌱 Sembrando casos de uso determinísticos en MongoDB Atlas...")
    try:
        await use_case_service.seed_initial_templates()
        logger.info("✨ Proceso completado exitosamente.")
    except Exception as e:
        logger.error(f"❌ Error al sembrar casos de uso: {e}")

if __name__ == "__main__":
    asyncio.run(main())
