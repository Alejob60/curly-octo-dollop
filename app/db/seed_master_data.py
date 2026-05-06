import asyncio
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings


PQRS_TYPES = [
    ("PETICION_GENERAL", "Peticion de interes general / particular", 1),
    ("PETICION_INFO", "Peticion de informacion", 2),
    ("CONSULTA", "Consulta", 3),
    ("QUEJA", "Queja", 4),
    ("RECLAMO", "Reclamo", 5),
    ("SUGERENCIA", "Sugerencia", 6),
    ("DENUNCIA_CORRUPCION", "Denuncia por actos de corrupcion", 7),
    ("PETICION_AUTORIDADES", "Peticion entre autoridades", 8),
]


DEPENDENCIES = [
    ("4173", "SECRETARIA DE MOVILIDAD", 1),
    ("4151", "SECRETARIA DE INFRAESTRUCTURA", 1),
    ("4145", "SECRETARIA DE SALUD PUBLICA", 1),
    ("4112", "SECRETARIA DE GOBIERNO", 1),
    ("4131", "SECRETARIA DE HACIENDA", 1),
    ("4133", "DATIC", 1),
    ("4114", "UAESP - BIENES Y SERVICIOS", 1),
    ("EMCALI", "EMCALI", 1),
]


async def seed_master_data() -> None:
    engine = create_async_engine(settings.get_database_url)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS pqrs_types (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(80) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    sort_order INT DEFAULT 1
                );
                """
            )
        )

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS cali_dependencies (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(20) UNIQUE,
                    name VARCHAR(255),
                    priority_level INT DEFAULT 1
                );
                """
            )
        )

        for code, name, sort_order in PQRS_TYPES:
            await conn.execute(
                text(
                    """
                    INSERT INTO pqrs_types (code, name, sort_order)
                    VALUES (:code, :name, :sort_order)
                    ON CONFLICT (code)
                    DO UPDATE SET name = EXCLUDED.name, sort_order = EXCLUDED.sort_order
                    """
                ),
                {"code": code, "name": name, "sort_order": sort_order},
            )

        for code, name, priority_level in DEPENDENCIES:
            await conn.execute(
                text(
                    """
                    INSERT INTO cali_dependencies (code, name, priority_level)
                    VALUES (:code, :name, :priority_level)
                    ON CONFLICT (code)
                    DO UPDATE SET name = EXCLUDED.name, priority_level = EXCLUDED.priority_level
                    """
                ),
                {"code": code, "name": name, "priority_level": priority_level},
            )

    await engine.dispose()
    print("master_data_seeded")


if __name__ == "__main__":
    asyncio.run(seed_master_data())
