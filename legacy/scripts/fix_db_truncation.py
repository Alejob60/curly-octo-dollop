import asyncio
from sqlalchemy import text
from app.core.db_clients import postgres_manager
from loguru import logger

async def fix_column_types():
    logger.info("🛠️ REPARANDO TIPOS DE DATOS EN POSTGRESQL...")
    
    queries = [
        # Cambiar campos cortos a TEXT para evitar truncamiento
        "ALTER TABLE cases_registry ALTER COLUMN asunto TYPE TEXT;",
        "ALTER TABLE cases_registry ALTER COLUMN peticionario_nombre TYPE TEXT;",
        "ALTER TABLE cases_registry ALTER COLUMN dependencia_nombre TYPE TEXT;",
        "ALTER TABLE cases_registry ALTER COLUMN routing_queue TYPE TEXT;",
        
        # Asegurar que campos JSON sean JSONB
        "ALTER TABLE cases_registry ALTER COLUMN completed_phases TYPE JSONB USING completed_phases::JSONB;",
        "ALTER TABLE cases_registry ALTER COLUMN citas_verificables TYPE JSONB USING citas_verificables::JSONB;",
        "ALTER TABLE cases_registry ALTER COLUMN pdf_paths TYPE JSONB USING pdf_paths::JSONB;",
        "ALTER TABLE cases_registry ALTER COLUMN pdf_hashes TYPE JSONB USING pdf_hashes::JSONB;"
    ]

    async with postgres_manager.engine.begin() as conn:
        for query in queries:
            try:
                await conn.execute(text(query))
                logger.success(f"Ejecutado: {query}")
            except Exception as e:
                logger.error(f"Error en query '{query}': {e}")
                
    logger.info("✅ Tipos de Datos Corregidos.")

if __name__ == "__main__":
    asyncio.run(fix_column_types())
