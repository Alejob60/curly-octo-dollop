from app.services.legal_agents.state import LegalCaseState
from app.services.legal_citation_engine import legal_citation_engine

class LegalResearcherAgent:
    async def validate_input(self, state: LegalCaseState) -> bool:
        # Relajamos: siempre intentamos investigar si hay texto de entrada
        return len(state.raw_input) > 10
    
    async def execute(self, state: LegalCaseState) -> dict:
        # Reutilizar tu RAG existente
        search_text = ' '.join(state.facts) if state.facts else state.raw_input
        query = f"{search_text} {state.case_type}"
        citations = await legal_citation_engine.get_citations_for_case(query, "4131") # General
        
        # En el futuro, agregar jurisprudencia aquí
        jurisprudence = []
            
        return {
            "legal_basis": citations,
            "jurisprudence": jurisprudence,
            "citations_block": self._format_citations(citations + jurisprudence)
        }
    
    def _format_citations(self, docs: list) -> str:
        if not docs: return "Sin citas legales específicas."
        return "\n".join([f"• {d.get('citacion_formato', 'Ley')} Art. {d.get('articulo', 'N/A')}: {d.get('texto_relevante', '')[:150]}..." for d in docs])
