import os
import json
import logging
from app.core.vertex_client import vertex_client

logger = logging.getLogger(__name__)
THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.85"))

class ConfidenceAuditor:
    """
    💎 MÓDULO 3: AUDITORÍA DE CONFIANZA (V65.12)
    Valida la correlación semántica entre la solicitud original y la respuesta de la IA.
    Bloquea la generación si el score es inferior al umbral (0.85).
    """
    
    def __init__(self, threshold: float = THRESHOLD):
        self.threshold = threshold

    async def evaluate(self, original_prompt: str, ai_response: dict) -> dict:
        """
        Realiza una autoevaluación semántica usando un prompt de auditoría ligera.
        """
        eval_prompt = (
            f"EVALÚA DEL 0 AL 1 LA CORRELACIÓN ENTRE:\n"
            f"1. SOLICITUD ORIGINAL: {original_prompt}\n"
            f"2. RESPUESTA IA (JSON): {json.dumps(ai_response, ensure_ascii=False)}\n"
            f"CRITERIOS DE EVALUACIÓN:\n"
            f"- Extracción completa de datos del peticionario.\n"
            f"- Normatividad específica citada del contexto RAG.\n"
            f"- Coherencia administrativa (Antecedentes, Análisis, Resolución).\n"
            f"- Ausencia de placeholders, mocks o alucinaciones.\n"
            f"RESPONDE ÚNICAMENTE CON UN JSON: {{'score': 0.XX, 'reason': '...'}}"
        )
        
        try:
            # Usar la interfaz directa para evitar validación recursiva
            raw_audit = await vertex_client.generate_content([eval_prompt])
            
            # Limpieza de JSON
            if "{" in raw_audit:
                raw_audit = raw_audit[raw_audit.find("{"):raw_audit.rfind("}")+1]
                
            audit_data = json.loads(raw_audit)
            score = float(audit_data.get("score", 0.0))
            
            logger.info(f"🔍 [AUDIT] Score: {score:.2f} | Threshold: {self.threshold}")
            
            return {
                "passed": score >= self.threshold,
                "score": score,
                "reason": audit_data.get("reason", "No reason provided"),
                "needs_human_review": score < self.threshold
            }

        except Exception as e:
            logger.error(f"❌ [AUDIT_ERROR] Fallo en evaluación: {e}")
            return {"passed": False, "score": 0.0, "reason": f"Error técnico auditoría: {e}", "needs_human_review": True}

confidence_auditor = ConfidenceAuditor()
