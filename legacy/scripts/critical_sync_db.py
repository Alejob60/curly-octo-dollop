import asyncio
from sqlalchemy import text
from app.core.db_clients import postgres_manager
from loguru import logger

async def critical_sync():
    logger.info("🛠️ INICIANDO SINCRONIZACIÓN CRÍTICA DE ESQUEMA V55.6...")
    
    queries = [
        # Asegurar columnas base de tiempo
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;",
        
        # Asegurar identificadores
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS session_id VARCHAR(100);",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS user_cc VARCHAR(20);",
        
        # Datos del ciudadano
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS peticionario_nombre VARCHAR(255);",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS peticionario_documento VARCHAR(50);",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS peticionario_email VARCHAR(150);",
        
        # Datos del caso y enrutamiento
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS asunto VARCHAR(255);",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS tipo_solicitud VARCHAR(100);",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS dependencia_id VARCHAR(10);",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS dependencia_nombre VARCHAR(200);",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT 'INICIADO';",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS current_phase VARCHAR(50) DEFAULT 'fase_1_ingesta';",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS completed_phases JSONB DEFAULT '[]';",
        
        # Consentimiento (Sprint 1.5)
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS consent_granted BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMP WITH TIME ZONE;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS consent_type VARCHAR(100);",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS consent_ip VARCHAR(50);",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS consent_signature_hash VARCHAR(255);",
        
        # Scores y Calidad
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 0.0;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS grounding_score FLOAT DEFAULT 0.0;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS review_score FLOAT DEFAULT 0.0;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS routing_queue VARCHAR(50) DEFAULT 'human_only';",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS urgencia_flag VARCHAR(20) DEFAULT 'NORMAL';",
        
        # Contenido IA
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS hechos_extraidos TEXT;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS soporte_traslado TEXT;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS borrador_proyeccion TEXT;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS citas_verificables JSONB DEFAULT '[]';",
        
        # Documentación y Firma
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS pdf_paths JSONB DEFAULT '{}';",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS pdf_hashes JSONB DEFAULT '{}';",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS signed_at TIMESTAMP WITH TIME ZONE;",
        "ALTER TABLE cases_registry ADD COLUMN IF NOT EXISTS signed_by VARCHAR(100);",
        
        # Índices de performance
        "CREATE INDEX IF NOT EXISTS idx_cases_session_v55 ON cases_registry(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_cases_radicado_v55 ON cases_registry(radicado);"
    ]

    async with postgres_manager.engine.begin() as conn:
        for query in queries:
            try:
                await conn.execute(text(query))
                logger.success(f"Ejecutado: {query[:60]}...")
            except Exception as e:
                logger.warning(f"Aviso en '{query[:40]}': {e}")
                
    logger.info("✅ Base de Datos Sincronizada con el Código.")

if __name__ == "__main__":
    asyncio.run(critical_sync())
