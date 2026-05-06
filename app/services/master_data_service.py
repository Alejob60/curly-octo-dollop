from __future__ import annotations

import re
from typing import Dict, List, Tuple

from loguru import logger
from sqlalchemy import select

from app.core.db_clients import AsyncSessionLocal
from app.models.sql_models import Dependency, PqrsType

class MasterDataService:
    async def get_master_data(self) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], str]:
        """
        REAL-DB: Recupera Master Data real desde PostgreSQL.
        """
        try:
            async with AsyncSessionLocal() as session:
                # 1. Consultar Tipos de PQRSD
                pqrs_result = await session.execute(select(PqrsType).order_by(PqrsType.id))
                pqrs_rows = pqrs_result.scalars().all()
                
                pqrs_types = [
                    {"id": str(p.id), "name": p.nombre} for p in pqrs_rows
                ]

                # 2. Consultar Dependencias
                dep_result = await session.execute(select(Dependency).filter(Dependency.es_activa == True).order_by(Dependency.id))
                dep_rows = dep_result.scalars().all()
                
                dependencies = [
                    {"id": str(d.id), "name": d.nombre} for d in dep_rows
                ]

                if pqrs_types and dependencies:
                    logger.info(f"Master Data recuperada de DB: {len(dependencies)} dependencias.")
                    return pqrs_types, dependencies, "database"
                
        except Exception as exc:
            logger.error(f"Error recuperando Master Data de DB: {exc}")

        # Fallback de seguridad (aunque con seed.py ya debería haber data)
        return [], [], "empty"

    async def suggest_dependency(self, topic: str, content: str, minimum_confidence: float = 0.85) -> Dict[str, object]:
        """
        Sugerencia básica por palabras clave (será reemplazado por Vertex AI en el flujo real).
        """
        # ... Mantener lógica de palabras clave si es necesario para fallback local ...
        return {
            "suggested_dependency_id": None,
            "confidence_score": 0.0,
            "suggested_dependency_name": None,
            "should_autoselect": False,
            "reasoning": "Sugerencia delegada al motor de Vertex AI.",
        }

master_data_service = MasterDataService()
