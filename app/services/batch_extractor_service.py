import asyncio
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sql_models import RadicadoLegacy
from app.core.db_clients import AsyncSessionLocal
from loguru import logger
import datetime
import random
import re

class BatchExtractorService:
    def _calculate_priority(self, asunto: str) -> str:
        """
        BCH-01.2: Motor de Priorización Rápida.
        Detección de urgencias legales y sociales.
        """
        asunto_lower = asunto.lower()
        
        # Criterios de ALTA PRIORIDAD
        if any(word in asunto_lower for word in ["tutela", "urgente", "salud", "vida", "riesgo", "niño", "anciano", "amenaza"]):
            return "ALTA"
        
        # Criterios de MEDIA PRIORIDAD
        if any(word in asunto_lower for word in ["hacienda", "impuesto", "cobro", "embargo", "vía", "hueco"]):
            return "MEDIA"
            
        return "BAJA"

    async def harvest_metadata(self, limit: int = 500, offset: int = 0):
        """
        BCH-01.1: Cosecha masiva con Triaje integrado.
        """
        logger.info(f"🚚 Iniciando cosecha masiva: {limit} registros desde offset {offset}...")
        
        # Simulación de respuesta de Orfeo con variedad de temas para probar priorización
        temas_simulados = [
            "Acción de TUTELA por falta de medicamentos",
            "Queja por hueco en la vía Calle 5",
            "Solicitud URGENTE de reparación de alcantarillado",
            "Consulta general sobre trámites de cultura",
            "Denuncia por RIESGO de colapso en fachada",
            "Petición de información sobre impuesto predial",
            "Sugerencia para mejorar atención en ventanilla",
            "Derecho de petición sobre protección de NIÑOS en parque"
        ]

        async with AsyncSessionLocal() as session:
            async with session.begin():
                for i in range(limit):
                    asunto = random.choice(temas_simulados)
                    prioridad = self._calculate_priority(asunto)
                    
                    legacy = RadicadoLegacy(
                        orfeo_id=f"2025-ORFEO-{offset + i + 1:06d}",
                        asunto=asunto,
                        fecha_radicacion_orfeo=datetime.datetime(2025, random.randint(1,12), random.randint(1,28)),
                        dependencia_orfeo=random.choice(["MOVILIDAD", "HACIENDA", "CULTURA", "SEGURIDAD", "SALUD"]),
                        estado_orbital="PENDIENTE_TRIAGE",
                        prioridad_ia=prioridad
                    )
                    session.add(legacy)
                
        logger.success(f"✅ Lote de {limit} indexado y PRIORIZADO exitosamente.")
        return limit

batch_extractor = BatchExtractorService()
