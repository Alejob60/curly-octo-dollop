import asyncio
from sqlalchemy import text
from app.core.db_clients import postgres_manager
from loguru import logger

async def migrate():
    """
    Agrega las columnas faltantes a cases_registry para GovTech V55.1
    """
    commands = [
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 0.0;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS routing_queue VARCHAR(50) DEFAULT 'human_only';",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS urgencia_flag VARCHAR(20) DEFAULT 'NORMAL';",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"
    ]
    
    try:
        async with postgres_manager.get_session() as session:
            for cmd in commands:
                logger.info(f"Ejecutando: {cmd}")
                await session.execute(text(cmd))
            await session.commit()
            logger.success("✅ Migración de cases_registry completada con éxito.")
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
