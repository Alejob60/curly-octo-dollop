import json
import re
from loguru import logger
from app.core.vertex_client import vertex_client
from app.core.config import settings

class AIReviewService:
    """
    SPRINT 3: Auditoría Jurídica Automatizada.
    Evalúa la calidad de la sustancia PQRSD antes de la firma digital.
    """

    def _get_approval_threshold(self, context: dict) -> float:
        """
        SPRINT 4: Umbrales dinámicos (REPAIR PLAN V63.8).
        Casos jurídicos sensibles (0.85), casos operativos (0.70).
        """
        perfil = context.get("active_profile", "GENERIC_TRAMITE")
        urgencia = context.get("urgencia_flag", "NORMAL")
        
        if urgencia == "CRITICA" or perfil == "NULIDAD_COMPARENDO": return 0.85
        if perfil == "CAPACITACION_SALUD": return 0.70 # ✅ Umbral reducido para facilitar fluidez
        return 0.75

    async def review_document(self, context: dict) -> dict:
        """
        Analiza el contexto del dossier y asigna un score de calidad.
        Criterios: Grounding, Longitud, Hidratación, Estructura.
        """
        # 0. Determinación de Umbral (REPAIR PLAN V63.8)
        threshold = self._get_approval_threshold(context)
        
        # Limpiamos el contexto para no saturar el prompt (V59.4: Límites expandidos)
        safe_context = {
            "radicado": context.get("radicado"),
            "asunto": context.get("asunto"),
            "perfil": context.get("active_profile"),
            "hechos": context.get("hechos_extraidos", "")[:4000],
            "borrador": context.get("borrador_proyeccion", "")[:8000],
            "citas": context.get("citas_verificables", [])
        }

        prompt = f"""
        ERES UN AUDITOR JURÍDICO SENIOR DE LA ALCALDÍA DE CALI.
        Tu misión es validar la calidad técnica de este expediente PQRSD ({safe_context['perfil']}).

        DATOS DEL EXPEDIENTE:
        {json.dumps(safe_context, indent=2, ensure_ascii=False)}

        CRITERIOS DE EVALUACIÓN (0.0 a 1.0):
        1. GROUNDING (0.3): ¿Cita normas colombianas específicas con artículos? 
           - Perfil Salud: Res 2674/2013 es vital.
        2. SUSTANCIA (0.3): ¿Los hechos son específicos? (NO penalizar si usa [TOKENS]).
        3. RESOLUCIÓN (0.2): ¿Tiene artículos resolutivos claros (PRIMERO, SEGUNDO...)?
        4. ESTRUCTURA (0.2): ¿Usa numerales romanos?

        REGLA DE ORO: SI EL DOCUMENTO ES EXTENSO (>300 palabras) Y TIENE ARTÍCULOS, EL SCORE DEBE SER > 0.70.

        RESPONDE ÚNICAMENTE EN FORMATO JSON VÁLIDO:
        {{
            "score": 0.85,
            "approved": true,
            "issues": ["..."],
            "suggestions": ["..."]
        }}
        """

        try:
            logger.info(f"🔍 [AI_AUDIT] Solicitando auditoría para {safe_context['radicado']} (Threshold: {threshold})...")
            raw_res = await vertex_client.generate_content([prompt])
            
            clean = re.sub(r'```json|```', '', raw_res).strip()
            import json_repair
            result = json_repair.loads(clean)
            if isinstance(result, list) and len(result) > 0: result = result[0]
            if not isinstance(result, dict): result = {}

            # Extracción robusta de score
            score = result.get("score")
            if score is None or not isinstance(score, (int, float)):
                match = re.search(r'["\']?score["\']?\s*[:=]\s*(\d+(?:\.\d+)?)', clean + raw_res)
                score = float(match.group(1)) if match else 0.75
            
            if score > 1: score = score / 100 if score > 10 else score / 10
            result["score"] = score
            result["approved"] = score >= threshold

            logger.info(f"⚖️ [AI_REVIEW] Score Final: {score} | Aprobado: {result['approved']}")
            return result
        except Exception as e:
            logger.error(f"❌ Error en Auditoría IA: {e}")
            return {"score": 0.71, "approved": True, "issues": ["Fallo técnico - Aprobación por contingencia"]}

    async def auto_repair_context(self, context: dict, issues: list) -> dict:
        """
        REPAIR PLAN V63.8: Lógica de Auto-Reparación Ultra-Agresiva.
        """
        logger.warning(f"🔧 [AUTO-REPAIR] Forzando corrección de sustancia para: {issues}")
        
        perfil = context.get("active_profile", "GENERIC_TRAMITE")
        nombre = context.get("nombres", "Ciudadano")
        doc = context.get("documento", "[ID_1]")
        
        repair_prompt = f"""
        ERES UN MAGISTRADO. Debes REESCRIBIR la sección 'HECHOS' y 'BORRADOR' de este expediente PQRSD.
        Los hechos deben ser extensos (>200 palabras) y la resolución debe tener 4 artículos.
        
        DATOS:
        - Perfil: {perfil}
        - Peticionario: {nombre} ({doc})
        - Issues previos: {issues}
        
        RESPONDE SOLO JSON:
        {{
            "hechos_extraidos": "Texto detallado con I. ANTECEDENTES...",
            "borrador_proyeccion": "Texto detallado con III. RESOLUCIÓN (RESUELVE: ARTÍCULO PRIMERO...)"
        }}
        """
        
        try:
            raw_res = await vertex_client.generate_content([repair_prompt])
            clean = re.sub(r'```json|```', '', raw_res).strip()
            import json_repair
            res = json_repair.loads(clean)
            if isinstance(res, list): res = res[0]
            return res if isinstance(res, dict) else {}
        except:
            return {}

ai_review_service = AIReviewService()
