from loguru import logger
from vertexai.generative_models import GenerativeModel
from app.services.conversation_manager import conversation_manager
from app.core.db_clients import mongo_db
import json

class DraftingService:
    def __init__(self):
        self.model = GenerativeModel("gemini-1.5-flash-001")

    async def project_background_response(self, radicado_data: dict) -> str:
        """
        AI-07: Proyecta una respuesta de fondo basada en el historial y la ley.
        """
        try:
            # 1. Recuperar contexto legal y precedentes desde Atlas
            context = await conversation_manager._get_context(radicado_data.get("asunto", ""))
            
            prompt = f"""
            Actúa como un Abogado Revisor de la Alcaldía de Cali. 
            Proyecta un BORRADOR DE RESPUESTA DE FONDO para el siguiente caso.
            
            CASO: {radicado_data.get('asunto')}
            CONTEXTO LEGAL: {context}
            
            REGLAS:
            - Usa un tono formal, técnico y administrativo.
            - Cita las leyes mencionadas en el contexto.
            - Indica claramente si se concede o se niega lo solicitado basado en la norma.
            - Deja espacios [ ] para que el abogado complete datos específicos de campo.
            """
            
            response = await self.model.generate_content_async(prompt)
            draft_text = response.text.strip()
            
            logger.info(f"Borrador de fondo proyectado para radicado {radicado_data.get('orfeo_id')}")
            return draft_text
            
        except Exception as e:
            logger.error(f"Error proyectando respuesta: {e}")
            return "No se pudo generar el borrador automático. Por favor proceda con redacción manual."

drafting_service = DraftingService()
