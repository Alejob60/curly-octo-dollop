import os
import json
from typing import List, Dict, Any, Optional
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.vertex_client import vertex_client

class LegalCitationEngine:
    """
    V55.3: Motor de Citas Legales con Soberanía Offline.
    ✅ RAG Atlas con Vector Search | ✅ Fallback Offline por Dependencia | ✅ Cero Vacíos.
    """
    def __init__(self):
        try:
            self.client = AsyncIOMotorClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)
            self.db = self.client[settings.MONGO_DB]
            self.collection = self.db.normativa_colombia
            logger.info(f"🚀 [RAG_ENGINE] Motor vinculado a Atlas (DB: {settings.MONGO_DB})")
        except Exception as e:
            logger.error(f"❌ Fallo al inicializar cliente Mongo: {e}")
            self.client = None

    async def get_citations_for_case(self, query_text: str = "", dependency_id: str = "", keywords: List[str] = None, limit: int = 5) -> List[Dict]:
        """Recupera leyes con triple capa de seguridad: Atlas -> Local Sectorial -> Local General."""
        
        # --- CAPA 1: BÚSQUEDA EN ATLAS ---
        if self.client:
            try:
                search_query = f"{query_text} {' '.join(keywords or [])} {dependency_id}".strip()
                embedding = await vertex_client.generate_embedding(search_query[:1000])
                
                pipeline = [
                    {"$vectorSearch": {
                        "index": "vector_index_normativa",
                        "path": "embedding",
                        "queryVector": embedding,
                        "numCandidates": 100,
                        "limit": limit
                    }},
                    {"$match": {"vigencia": True}},
                    {"$project": {
                        "citacion_formato": 1, "articulo": 1, "texto_relevante": 1,
                        "ente_emisor": 1, "vigencia_desde": 1, "_id": 0
                    }}
                ]
                
                cursor = self.collection.aggregate(pipeline)
                results = await cursor.to_list(length=limit)
                if results:
                    logger.success(f"📚 [RAG_ATLAS] {len(results)} leyes recuperadas con éxito.")
                    return results
            except Exception as e:
                logger.warning(f"⚠️ Fallo Atlas (Auth/Red): {e}. Activando Soberanía Offline...")

        # --- CAPA 2: SOBERANÍA OFFLINE SECTORIAL ---
        logger.info(f"🛡️ [RAG_OFFLINE] Aplicando normativa por dependencia: {dependency_id}")
        return await self._get_offline_laws(dependency_id)

    async def _get_offline_laws(self, dependency_id: str) -> List[Dict]:
        """Base de datos legal estática para alta disponibilidad."""
        OFFLINE_DB = {
            "4152": [ # Movilidad
                {"citacion_formato": "Ley 769 de 2002", "articulo": "131", "texto_relevante": "El procedimiento de las fotodetecciones debe cumplir con requisitos de notificación personal y material probatorio.", "ente_emisor": "Congreso de la República", "vigencia_desde": "2002"},
                {"citacion_formato": "Ley 1843 de 2017", "articulo": "8", "texto_relevante": "El comparendo digital debe ser notificado personalmente al infractor en la última dirección registrada en el RUNT.", "ente_emisor": "Congreso de la República", "vigencia_desde": "2017"}
            ],
            "4135": [ # Salud
                {"citacion_formato": "Ley 1751 de 2015", "articulo": "2", "texto_relevante": "El derecho fundamental a la salud es autónomo e irrenunciable. Comprende el acceso oportuno y de calidad.", "ente_emisor": "Congreso de la República", "vigencia_desde": "2015"},
                {"citacion_formato": "Resolución 2674 de 2013", "articulo": "12", "texto_relevante": "El personal manipulador de alimentos debe recibir capacitación en educación sanitaria y prácticas higiénicas.", "ente_emisor": "Ministerio de Salud", "vigencia_desde": "2013"}
            ],
            "4146": [ # Infraestructura
                {"citacion_formato": "Ley 105 de 1993", "articulo": "3", "texto_relevante": "Las vías públicas deben mantenerse en condiciones seguras para el tránsito. Responsabilidad municipal.", "ente_emisor": "Congreso de la República", "vigencia_desde": "1993"},
                {"citacion_formato": "Ley 1523 de 2012", "articulo": "5", "texto_relevante": "La gestión del riesgo de desastres incluye la identificación, reducción de riesgos y atención de emergencias.", "ente_emisor": "Congreso de la República", "vigencia_desde": "2012"}
            ],
            "4131": [ # Hacienda / General
                {"citacion_formato": "Ley 1755 de 2015", "articulo": "13", "texto_relevante": "Toda persona tiene derecho a presentar peticiones respetuosas a las autoridades y a obtener pronta resolución.", "ente_emisor": "Congreso de la República", "vigencia_desde": "2015"},
                {"citacion_formato": "CPACA (Ley 1437 de 2011)", "articulo": "21", "texto_relevante": "Si la autoridad no es competente, debe informar al interesado y remitir a la entidad correspondiente.", "ente_emisor": "Congreso de la República", "vigencia_desde": "2011"}
            ]
        }
        return OFFLINE_DB.get(str(dependency_id), OFFLINE_DB["4131"])

    async def get_emergency_fallback(self) -> List[Dict]:
        return await self._get_offline_laws("4131")

    async def search_relevant_laws(self, query_text: str, limit: int = 5) -> List[Dict]:
        return await self.get_citations_for_case(query_text=query_text, limit=limit)

    async def get_standardized_citations(self, tags: List[str], limit: int = 3) -> List[Dict]:
        return await self.get_citations_for_case(keywords=tags, limit=limit)

legal_citation_engine = LegalCitationEngine()
