"""
Pre-Render Validator - Validación estricta antes de generar PDFs
Versión: V58.0 - Fix: bloqueo de tokens pendientes + validación de sustancia
"""

import re
import logging
from typing import Dict, List, Optional
from app.core.vertex_client import vertex_client
from loguru import logger

logger = logging.getLogger(__name__)


class PreRenderValidator:
    """Validador preventivo: bloquea generación si hay tokens o sustancia insuficiente"""
    
    async def validate_substance_with_ai(self, context: Dict) -> Dict:
        """
        Validación en dos capas:
        1. Reglas locales estrictas (tokens, campos vacíos)
        2. Auditoría IA para calidad jurídica
        """
        # 🔥 CAPA 1: Validación local estricta (ANTES de llamar a IA)
        local_validation = self._validate_local_rules(context)
        if not local_validation['valid']:
            logger.error(f"🔒 [PRE-RENDER] Validación local fallida: {local_validation['errors']}")
            return {
                "status": "REJECTED",
                "reason": "Validación local fallida",
                "quality_score": 0.0,
                "errors": local_validation['errors'],
                "action_required": "Corregir tokens o campos vacíos antes de continuar"
            }
        
        # 🔥 CAPA 2: Validación IA para calidad jurídica
        ai_validation = await self._validate_with_ai(context)
        
        # Combinar resultados
        return {
            "status": "APPROVED" if ai_validation.get('approved', False) else "REJECTED",
            "quality_score": ai_validation.get('score', 0.0),
            "reason": ai_validation.get('reason'),
            "issues": ai_validation.get('issues', []),
            "suggestions": ai_validation.get('suggestions', []),
            "grounding_score": ai_validation.get('grounding_score', 0.0),
            "substance_score": ai_validation.get('substance_score', 0.0),
            "structure_score": ai_validation.get('structure_score', 0.0),
        }
    
    def _validate_local_rules(self, context: Dict) -> Dict:
        """
        Validación local estricta: tokens, campos vacíos, estructura mínima.
        """
        errors = []
        
        # 1. Validar tokens pendientes en campos críticos
        fields_critical = ["borrador_proyeccion", "hechos_extraidos", "soporte_traslado"]
        for field in fields_critical:
            value = context.get(field, "")
            if isinstance(value, str):
                tokens = re.findall(r'\[[A-Z_0-9ÁÉÍÓÚÑ]+\]', value)
                allowed = ["[Día]", "[Mes]", "[Año]"]  # Solo fechas permitidas
                forbidden = [t for t in tokens if t not in allowed]
                if forbidden:
                    errors.append(f"Tokens pendientes en '{field}': {forbidden}")
        
        # 2. Validar campos vacíos o genéricos
        if not context.get("borrador_proyeccion") or context.get("borrador_proyeccion") in ["", "En análisis administrativo de fondo."]:
            errors.append("borrador_proyeccion está vacío o genérico")
        
        if not context.get("hechos_extraidos") or len(context.get("hechos_extraidos", "")) < 50:
            errors.append("hechos_extraidos insuficiente")
        
        # 3. Validar grounding mínimo
        citations = context.get("citas_verificables", [])
        if not citations or len(citations) < 1:
            errors.append("Sin grounding jurídico verificable")
        
        # 4. Validar dependencia coherente
        if not context.get("dependencia_gestora") or context.get("dependencia_gestora") == "Secretaría General":
            # Warning: General es válido como punto de entrada, pero proyección debe ser competente
            if context.get("problem_type") in ["infraestructura_vial", "movilidad_comparendos"] and not context.get("projection_dependency_name"):
                errors.append("Proyección sin dependencia competente definida")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _validate_with_ai(self, context: Dict) -> Dict:
        """Validación de calidad jurídica con IA"""
        prompt = f"""
        AUDITORÍA JURÍDICA PQRSD (RESPONDE SOLO JSON):
        
        CONTEXTO:
        - Tipo: {context.get('problem_type', 'general')}
        - Dependencia: {context.get('dependencia_gestora')}
        - Grounding: {context.get('citations_block', '')[:300]}
        - Borrador: {context.get('borrador_proyeccion', '')[:1500]}
        
        EVALÚA (0-1 cada dimensión):
        1. GROUNDING: ¿Citas son específicas del problema? (no genéricas)
        2. SUBSTANCIA: ¿Borrador tiene análisis técnico personalizado?
        3. ESTRUCTURA: ¿Tiene Hechos+Fundamentos+Resolución clara?
        4. PII: ¿Datos personales protegidos con tokens [NOMBRE_1]?
        
        UMBRAL APROBACIÓN: 0.75
        
        RESPONDE EXACTAMENTE:
        {{
          "score": 0.XX,
          "approved": true/false,
          "grounding_score": 0.XX,
          "substance_score": 0.XX,
          "structure_score": 0.XX,
          "issues": ["issue1", "issue2"],
          "suggestions": ["suggestion1"]
        }}
        """
        
        try:
            response = await vertex_client.generate_content([prompt])
            import json
            import re
            clean = re.sub(r'```json|```', '', response).strip()
            return json.loads(clean)
        except Exception as e:
            logger.error(f"❌ Error en validación IA: {e}")
            return {
                "score": 0.0,
                "approved": False,
                "reason": f"Error en validación IA: {str(e)}"
            }
