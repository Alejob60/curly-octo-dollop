from app.services.legal_agents.state import LegalCaseState
from app.core.vertex_client import vertex_client
import json
import re

class ComplianceReviewerAgent:
    async def validate_input(self, state: LegalCaseState) -> bool:
        return state.draft_document is not None
        
    async def execute(self, state: LegalCaseState) -> dict:
        prompt = f"""
        ERES UN AUDITOR JURÍDICO SENIOR. 
        Revisa el cumplimiento legal del siguiente borrador y responde EXCLUSIVAMENTE con un objeto JSON válido.
        
        TIPO: {state.case_type}
        BORRADOR: {state.draft_document[:3000]}
        BASE LEGAL: {state.citations_block}
        
        FORMATO DE RESPUESTA (JSON ESTRICTO):
        {{
            "status": "approved" | "draft" | "rejected",
            "notes": ["nota 1", "nota 2"],
            "missing": ["elemento faltante 1"],
            "score": 0.0 a 1.0
        }}
        """
        
        res = await vertex_client.generate_content([prompt])
        clean = re.sub(r'```json|```', '', res).strip()
        try:
            import json_repair
            data = json_repair.loads(clean)
            if isinstance(data, list) and len(data) > 0: data = data[0]
            if not isinstance(data, dict):
                raise ValueError("Respuesta no es un objeto")
        except:
            logger.warning(f"⚠️ [AGENT_REVIEWER] Fallo al parsear auditoría. Usando fallback.")
            data = {"status": "draft", "notes": ["Error al auditar - Respuesta malformada"], "score": 0.5}
        
        return {
            "review_status": data.get("status", "draft"),
            "notes": data.get("notes", []),
            "missing": data.get("missing", []),
            "score": data.get("score", 0.5)
        }
