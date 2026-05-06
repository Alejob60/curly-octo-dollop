"""
Adaptive RAG - Recuperación de grounding jurídico adaptativo
Versión: V58.1 - Fix: filtrado por relevancia específica del problema
"""

from typing import List, Dict, Optional
from app.services.legal_citation_engine import legal_citation_engine
from loguru import logger


class AdaptiveRAG:
    """
    Sistema de recuperación adaptativa:
    1. Prioriza leyes específicas del tipo de problema
    2. Filtra leyes irrelevantes
    3. Asegura normas técnicas clave según sector
    """
    
    # Mapeo: tipo de problema → leyes específicas requeridas
    PROBLEM_REQUIRED_LAWS = {
        "capacitacion_comunitaria": [
            {"citacion_formato": "Resolución 2674 de 2013", "articulo": "12",
             "texto_relevante": "El personal manipulador de alimentos debe recibir capacitación en educación sanitaria y prácticas higiénicas.",
             "ente_emisor": "Ministerio de Salud", "vigencia_desde": "2013"},
            {"citacion_formato": "Ley 9 de 1979", "articulo": "243",
             "texto_relevante": "Toda persona que manipule alimentos deberá observar las normas de higiene y sanidad.",
             "ente_emisor": "Congreso de la República", "vigencia_desde": "1979"},
        ],
        "infraestructura_vial": [
            {"citacion_formato": "Ley 105 de 1993", "articulo": "3",
             "texto_relevante": "Las vías públicas deben mantenerse en condiciones seguras para el tránsito. Responsabilidad municipal.",
             "ente_emisor": "Congreso de la República", "vigencia_desde": "1993"},
            {"citacion_formato": "Ley 1523 de 2012", "articulo": "5",
             "texto_relevante": "La gestión del riesgo de desastres incluye la identificación, reducción de riesgos y atención de emergencias.",
             "ente_emisor": "Congreso de la República", "vigencia_desde": "2012"},
        ],
        "movilidad_comparendos": [
            {"citacion_formato": "Ley 769 de 2002", "articulo": "131",
             "texto_relevante": "El procedimiento de las fotodetecciones debe cumplir con requisitos de notificación personal.",
             "ente_emisor": "Congreso de la República", "vigencia_desde": "2002"},
            {"citacion_formato": "Ley 1843 de 2017", "articulo": "8",
             "texto_relevante": "El comparendo digital debe ser notificado personalmente al infractor.",
             "ente_emisor": "Congreso de la República", "vigencia_desde": "2017"},
        ],
        "salud_urgencia": [
            {"citacion_formato": "Ley 1751 de 2015", "articulo": "2",
             "texto_relevante": "El derecho fundamental a la salud es autónomo e irrenunciable. Comprende el acceso oportuno y de calidad.",
             "ente_emisor": "Congreso de la República", "vigencia_desde": "2015"},
        ],
    }
    
    # Leyes a EXCLUIR por tipo de problema (irrelevantes)
    PROBLEM_EXCLUDED_LAWS = {
        "capacitacion_comunitaria": ["Ley 1751 de 2015"],  # Salud estatutaria no aplica directamente
        "infraestructura_vial": ["Ley 1751 de 2015"],  # No es tema de salud estatutaria
        "movilidad_comparendos": ["Ley 1751 de 2015"],  # No aplica a tránsito
    }
    
    async def retrieve_grounding(
        self, 
        query: str, 
        dependency_id: str, 
        problem_type: str,
        confidence: float
    ) -> List[Dict]:
        """
        Recupera grounding adaptado: específico + filtrado + deduplicado.
        """
        citations = []
        
        # Paso 1: Agregar leyes REQUERIDAS específicas del problema
        if problem_type in self.PROBLEM_REQUIRED_LAWS:
            required = self.PROBLEM_REQUIRED_LAWS[problem_type]
            citations.extend(required)
            logger.info(f"📚 [ADAPTIVE_RAG] +{len(required)} leyes requeridas para {problem_type}")
        
        # Paso 2: Recuperar leyes genéricas de la dependencia (fallback)
        dependency_citations = await legal_citation_engine.get_citations_for_case(query, dependency_id)
        
        # Paso 3: Filtrar leyes IRRELEVANTES según tipo de problema
        excluded = self.PROBLEM_EXCLUDED_LAWS.get(problem_type, [])
        filtered = [c for c in dependency_citations if c.get("citacion_formato") not in excluded]
        
        # Paso 4: Evitar duplicados (priorizar específicas sobre genéricas)
        existing_formats = {c.get("citacion_formato") for c in citations}
        for cit in filtered:
            if cit.get("citacion_formato") not in existing_formats:
                citations.append(cit)
                existing_formats.add(cit.get("citacion_formato"))
        
        # Paso 5: Limitar a 4 citas más relevantes (específicas primero)
        return self._rank_and_limit(citations, problem_type, limit=4)
    
    def _rank_and_limit(self, citations: List[Dict], problem_type: str, limit: int = 4) -> List[Dict]:
        """Ordena por relevancia y limita el número de citas"""
        
        # Puntaje: leyes requeridas = 2.0, otras = 1.0
        required_formats = {c["citacion_formato"] for c in self.PROBLEM_REQUIRED_LAWS.get(problem_type, [])}
        
        def citation_score(cit: Dict) -> float:
            return 2.0 if cit.get("citacion_formato") in required_formats else 1.0
        
        # Ordenar descendente y limitar
        ranked = sorted(citations, key=citation_score, reverse=True)
        return ranked[:limit]
    
    def get_local_citation(self, law_format: str) -> Optional[Dict]:
        """Retorna cita desde base local si no está en RAG"""
        for problem_laws in self.PROBLEM_REQUIRED_LAWS.values():
            for law in problem_laws:
                if law["citacion_formato"] == law_format:
                    return law
        return None

hermes_rag = AdaptiveRAG()

