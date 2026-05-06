import json
from typing import Dict, Any, List, Optional
from loguru import logger
from app.core.vertex_client import vertex_client
from app.core.db_clients import redis_client

class CopilotEngine:
    """
    V56.1: Motor de Asistencia IA Contextual (Copiloto GovTech).
    Proporciona resúmenes, explicaciones de grounding y soporte jurídico en tiempo real.
    """

    async def generate_response(self, session_id: str, query: str, user_id: str) -> Dict[str, Any]:
        """
        Genera una respuesta contextual basada en el estado actual del expediente.
        """
        # 1. Recuperar contexto completo del caso desde Valkey
        state_key = f"pqrs:state:{session_id}"
        case_data = await redis_client.hgetall(state_key)

        if not case_data:
            return {"response": "No se encontró contexto para este expediente.", "sources": []}

        # 2. Construir Prompt de Copiloto
        prompt = f"""
        ERES EL COPILOTO JURÍDICO DE LA ALCALDÍA DE CALI.
        Estás asistiendo al funcionario {user_id} en el análisis de un expediente PQRSD.

        DATOS DEL EXPEDIENTE:
        - Radicado: {case_data.get('radicado')}
        - Dependencia: {case_data.get('dependencia_competente')}
        - AI Confidence Score: {case_data.get('ai_score')}
        - Hechos Extraídos: {case_data.get('hechos_extraidos', '')[:1000]}
        - Grounding Legal (Citas): {case_data.get('citas_verificables', '[]')}

        PREGUNTA DEL FUNCIONARIO: "{query}"

        INSTRUCCIONES PARA TU RESPUESTA:
        1. Responde de forma concisa y profesional.
        2. Si preguntan por el score de confianza, explica basándote en la calidad de los hechos y la presencia de leyes.
        3. Si preguntan por leyes, cita específicamente las que están en el "Grounding Legal".
        4. Si la información no está en el expediente, di que "se requiere revisión manual del documento original".
        5. Usa Markdown para resaltar puntos clave.

        RESPONDE SOLO EL TEXTO DE LA RESPUESTA.
        """

        try:
            response_text = await vertex_client.generate_content([prompt])
            logger.info(f"🤖 [COPILOT] Respuesta generada para sesión {session_id}")
            
            return {
                "response": response_text,
                "sources": json.loads(case_data.get("citas_verificables", "[]")),
                "session_id": session_id
            }
        except Exception as e:
            logger.error(f"❌ Error en CopilotEngine: {e}")
            return {"response": "Error interno al procesar la consulta con IA.", "sources": []}

copilot_engine = CopilotEngine()
