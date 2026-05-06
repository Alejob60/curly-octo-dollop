import re
from loguru import logger
from app.services.rag_service import rag_service

class GroundingValidator:
    """
    ⚖️ Módulo 3: Validador de Grounding Jurídico.
    Extrae citas del LLM y las valida contra la base de datos oficial.
    """
    # Patrón para detectar Leyes, Sentencias y Decretos
    CITATION_PATTERN = re.compile(
        r'(Ley\s+\d+\s+de\s+\d+|Sentencia\s+[A-Z]-\d+/\d+|Decreto\s+\d+\s+de\s+\d+)', 
        re.IGNORECASE
    )

    async def validate_content(self, text: str, dependency_id: str) -> dict:
        """
        Analiza un texto y devuelve el ratio de veracidad legal.
        """
        citations_found = list(set(self.CITATION_PATTERN.findall(text)))
        
        if not citations_found:
            return {
                "status": "NO_CITATIONS",
                "ratio": 0.0,
                "message": "No se detectaron citas legales para validar."
            }

        valid_count = 0
        invalid_citations = []

        for cit in citations_found:
            # Buscar en MongoDB si la cita existe y es vigente
            # (Usamos búsqueda de texto simple en este paso de validación)
            is_valid = await rag_service.search_legal_normative(cit, limit=1)
            
            if is_valid:
                valid_count += 1
            else:
                invalid_citations.append(cit)

        ratio = valid_count / len(citations_found)
        approved = ratio >= 0.95

        logger.info(f"⚖️ Grounding: {valid_count}/{len(citations_found)} citas válidas. Ratio: {ratio:.2f}")

        return {
            "status": "APPROVED" if approved else "REVIEW_REQUIRED",
            "ratio": ratio,
            "valid_citations": valid_count,
            "total_citations": len(citations_found),
            "invalid": invalid_citations
        }

grounding_validator = GroundingValidator()
