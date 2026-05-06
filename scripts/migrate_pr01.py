import asyncio
from sqlalchemy import text
from app.core.db_clients import postgres_manager
from loguru import logger

async def migrate_pr01():
    logger.info("🚀 INICIANDO MIGRACIÓN DE INTEROPERABILIDAD PR-01...")
    
    queries = [
        # Nuevas columnas para interoperabilidad con Orfeo/SAUL
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS orfeo_id VARCHAR(100) UNIQUE;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS vencimiento_legal TIMESTAMP WITH TIME ZONE;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS alerta_vencimiento VARCHAR(20) DEFAULT 'VERDE';",
        
        # Índices para búsqueda rápida en el dashboard
        "CREATE INDEX IF NOT EXISTS idx_cases_orfeo_id ON cases_registry(orfeo_id);"
    ]

    async with postgres_manager.engine.begin() as conn:
        for query in queries:
            try:
                await conn.execute(text(query))
                logger.success(f"Ejecutado: {query[:60]}...")
            except Exception as e:
                logger.warning(f"Nota: {e}")
                
    logger.info("✅ Esquema de Interoperabilidad Sincronizado.")

if __name__ == "__main__":
    asyncio.run(migrate_pr01())
