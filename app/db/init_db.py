import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import logging

# Permite ejecutar: python app/db/init_db.py
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings

logger = logging.getLogger(__name__)

async def init_db():
    engine = create_async_engine(settings.get_database_url)
    
    queries = [
        "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";",
        "CREATE EXTENSION IF NOT EXISTS vector;",
        # Eliminamos el type si ya existe para evitar errores en re-ejecución
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'input_source') THEN CREATE TYPE input_source AS ENUM ('LEGACY_SYSTEM', 'DIRECT_PORTAL'); END IF; END $$;",
        """
        CREATE TABLE IF NOT EXISTS pqrsd_registry (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            external_id VARCHAR(50) UNIQUE NOT NULL,
            tenant_id VARCHAR(20) DEFAULT 'CALI-01',
            source_type input_source DEFAULT 'LEGACY_SYSTEM',
            citizen_id VARCHAR(20),
            citizen_name VARCHAR(100),
            citizen_email VARCHAR(100),
            status VARCHAR(30) DEFAULT 'RECEIVED',
            priority VARCHAR(10) DEFAULT 'NORMAL',
            risk_level VARCHAR(20),
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            deadline_at DATE,
            task_id VARCHAR(100),
            attachment_url TEXT,
            scheduled_release_at TIMESTAMP,
            is_finalized BOOLEAN DEFAULT FALSE,
            target_department_id VARCHAR(20),
            is_emergency BOOLEAN DEFAULT FALSE
        );
        """,
        "ALTER TABLE pqrsd_registry ADD COLUMN IF NOT EXISTS is_emergency BOOLEAN DEFAULT FALSE;",
        """
        CREATE TABLE IF NOT EXISTS cali_dependencies (
            id SERIAL PRIMARY KEY,
            code VARCHAR(20) UNIQUE,
            name VARCHAR(255),
            priority_level INT DEFAULT 1
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS pqrs_types (
            id SERIAL PRIMARY KEY,
            code VARCHAR(80) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            sort_order INT DEFAULT 1
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name VARCHAR(255),
            tenant_id VARCHAR(50) DEFAULT 'orbitalprime',
            role VARCHAR(20) DEFAULT 'USER',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS legal_precedents (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            case_type VARCHAR(50),
            decision_outcome VARCHAR(20),
            legal_argument TEXT,
            source_url TEXT,
            embedding VECTOR(768),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_ledger (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            registry_id VARCHAR(50) NOT NULL,
            action VARCHAR(120) NOT NULL,
            previous_hash TEXT,
            current_hash TEXT,
            payload JSONB,
            transaction_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS trazabilidad (
            id SERIAL PRIMARY KEY,
            external_id VARCHAR(50) NOT NULL,
            estado_anterior VARCHAR(50),
            estado_nuevo VARCHAR(50) NOT NULL,
            id_funcionario VARCHAR(100),
            fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            comentario TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS evidencias_bucket (
            id SERIAL PRIMARY KEY,
            external_id VARCHAR(50) NOT NULL,
            gcs_uri TEXT NOT NULL,
            tipo_documento VARCHAR(50),
            fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "ALTER TABLE audit_ledger ADD COLUMN IF NOT EXISTS registry_id VARCHAR(50);",
        "ALTER TABLE audit_ledger ADD COLUMN IF NOT EXISTS action VARCHAR(120);",
        "ALTER TABLE audit_ledger ADD COLUMN IF NOT EXISTS previous_hash TEXT;",
        "ALTER TABLE audit_ledger ADD COLUMN IF NOT EXISTS current_hash TEXT;",
        "ALTER TABLE audit_ledger ADD COLUMN IF NOT EXISTS payload JSONB;",
        "ALTER TABLE audit_ledger ADD COLUMN IF NOT EXISTS transaction_id TEXT;",
        "ALTER TABLE audit_ledger ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
    ]
    
    for query in queries:
        query_head = query.strip().splitlines()[0][:60]
        try:
            async with engine.begin() as conn:
                await conn.execute(text(query))
            logger.info(f"Procesando: {query_head}...")
        except Exception as e:
            message = str(e)
            if "extension \"vector\" is not allow-listed" in message:
                logger.warning(
                    "pgvector no permitido en este Azure PostgreSQL; se omite la creación de la extensión."
                )
            elif "VECTOR(" in query.upper() or "::vector" in query:
                logger.warning(
                    "Se omite objeto dependiente de pgvector porque la extensión no está disponible."
                )
            else:
                logger.error(f"Error ejecutando '{query_head}...': {message}")
    
    await engine.dispose()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(init_db())
