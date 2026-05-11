import asyncio
from sqlalchemy import text
from app.core.db_clients import postgres_manager
from loguru import logger

async def fix():
    logger.info("🛠️ Finalizando sincronización de campos de scoring...")
    async with postgres_manager.engine.begin() as conn:
        await conn.execute(text("ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS substance_score FLOAT DEFAULT 0.0;"))
        await conn.execute(text("ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS structure_score FLOAT DEFAULT 0.0;"))
    logger.success("✅ DB sincronizada.")

if __name__ == "__main__":
    asyncio.run(fix())
