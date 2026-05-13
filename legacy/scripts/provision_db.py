import asyncio
from app.core.db_clients import postgres_manager, Base
from app.models.sql_models import UserProfile, CaseRegistry, CitizenVault, SessionToken
from loguru import logger

async def provision_database():
    logger.info("🚀 Iniciando provisión de tablas en PostgreSQL...")
    try:
        async with postgres_manager.engine.begin() as conn:
            # Esto creará las tablas si no existen
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Tablas 'user_profiles' y 'cases_registry' creadas exitosamente.")
    except Exception as e:
        logger.error(f"❌ Error al provisionar DB: {e}")

if __name__ == "__main__":
    asyncio.run(provision_database())
