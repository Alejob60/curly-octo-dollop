import re
from loguru import logger
from typing import Dict, Any, List

class UseCaseValidator:
    """
    USECASE-2.4: Validador post-generación de reglas.
    Asegura que la IA cumpla con el grounding y las restricciones de negocio.
    """
    
    async def validate_response(self, response_text: str, matched_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Revisa si la respuesta de la IA cumple con las reglas del caso de uso.
        """
        if not matched_case:
            return {"is_valid": True}

        errors = []
        
        # 1. Verificar Citas Obligatorias (Grounding)
        mandatory = matched_case.get("mandatory_citations", [])
        for citation in mandatory:
            # Buscamos partes clave de la cita (ej: 'C-038' o '1751')
            citation_keyword = re.search(r'(?:Ley|Sentencia|Decreto)\s+([A-Z0-9\-/]+)', citation, re.I)
            if citation_keyword:
                kw = citation_keyword.group(1)
                if kw.lower() not in response_text.lower():
                    errors.append(f"Falta citar la norma obligatoria: {kw}")

        # 2. Verificar Entidades Prohibidas (Privacy/Logic)
        forbidden = matched_case.get("forbidden_entities", [])
        for entity in forbidden:
            if entity.replace("_", " ") in response_text.lower():
                errors.append(f"La IA solicitó o mencionó un dato prohibido para este caso: {entity}")

        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"⚠️ Validación de Reglas Fallida: {errors}")
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "suggested_retry_prompt": f"Tu respuesta anterior omitió estas reglas obligatorias: {', '.join(errors)}. Por favor, corrige la respuesta." if not is_valid else None
        }

use_case_validator = UseCaseValidator()
