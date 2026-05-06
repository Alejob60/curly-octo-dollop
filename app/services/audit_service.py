from loguru import logger
from vertexai.generative_models import GenerativeModel
import json

class AIAuditService:
    def __init__(self):
        self.auditor_model = GenerativeModel("gemini-1.5-pro-001")
        self.system_instruction = """
        Eres el Auditor Jurídico Senior de la Alcaldía de Cali.
        Tu trabajo NO es redactar, sino AUDITAR el trabajo de la IA de Nivel 1.
        
        CRITERIOS DE AUDITORÍA:
        1. ¿Cita correctamente la Ley 1755 de 2015?
        2. ¿Menciona la dependencia competente según el Decreto 0516?
        3. ¿El tono es institucional y empático?
        4. ¿Cumple con el Derecho de Petición?
        
        Si el documento falla en CUALQUIER punto, debes rechazarlo con el motivo exacto.
        """

    async def audit_document(self, document_content: str, context: str) -> dict:
        """
        AUDIT-01: Procesa el documento generado y emite un veredicto de conformidad.
        """
        prompt = f"""
        AUDITA EL SIGUIENTE ACTO ADMINISTRATIVO:
        ---
        {document_content}
        ---
        CONTEXTO LEGAL:
        {context}
        
        RESPONDE EN JSON:
        {{
            "status": "APPROVED" | "REJECTED",
            "conformity_score": 0.0-1.0,
            "findings": ["lista de errores o mejoras"],
            "law_cited_correctly": bool
        }}
        """
        
        try:
            response = await self.auditor_model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            verdict = json.loads(response.text)
            logger.info(f"Auditoría IA completada. Score: {verdict.get('conformity_score')}")
            return verdict
        except Exception as e:
            logger.error(f"Fallo en motor de auditoría IA: {e}")
            return {"status": "PENDING_HUMAN", "conformity_score": 0.5, "findings": ["Error técnico en auditoría"]}

ai_audit_service = AIAuditService()
