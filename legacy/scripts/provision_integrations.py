import asyncio
from sqlalchemy import text
from app.core.db_clients import postgres_manager
from loguru import logger

async def provision_integrations():
    logger.info("🚀 PROVISIONANDO TABLA DE INTEGRACIONES PR-01...")
    
    query = """
    CREATE TABLE IF NOT EXISTS integration_connectors (
        id VARCHAR(50) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        system_type VARCHAR(50) NOT NULL,
        protocol VARCHAR(50) NOT NULL,
        config JSONB NOT NULL,
        field_mapping JSONB,
        sync_mode VARCHAR(20) DEFAULT 'polling',
        sync_interval INTEGER DEFAULT 900,
        last_sync_at TIMESTAMP WITH TIME ZONE,
        last_sync_status VARCHAR(50),
        health_status VARCHAR(20) DEFAULT 'unknown',
        last_error TEXT,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """

    async with postgres_manager.engine.begin() as conn:
        try:
            await conn.execute(text(query))
            logger.success("✅ Tabla 'integration_connectors' creada/verificada.")
        except Exception as e:
            logger.error(f"❌ Error al crear tabla de integraciones: {e}")

if __name__ == "__main__":
    asyncio.run(provision_integrations())
