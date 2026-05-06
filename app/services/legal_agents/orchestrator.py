from app.services.legal_agents.state import LegalCaseState
from app.services.legal_agents.extractor import FactExtractorAgent
from app.services.legal_agents.researcher import LegalResearcherAgent
from app.services.legal_agents.crafter import DocumentCrafterAgent
from app.services.legal_agents.reviewer import ComplianceReviewerAgent
from app.services.persistence_bridge import persistence_bridge
from loguru import logger
import asyncio

class LegalOrchestrator:
    """
    Cerebro Multiagente V1.0.
    Coordina agentes especializados para el escalado legal de Orbital Prime.
    """
    def __init__(self):
        self.agents = {
            "extractor": FactExtractorAgent(),
            "researcher": LegalResearcherAgent(),
            "crafter": DocumentCrafterAgent(),
            "reviewer": ComplianceReviewerAgent()
        }
    
    async def process(self, session_id: str, raw_input: str, case_type: str = "pqrs", extra_prompt: str = None) -> LegalCaseState:
        logger.info(f"🧠 [LEGAL_ORCHESTRATOR] Iniciando proceso para {case_type} | Session: {session_id}")
        state = LegalCaseState(session_id=session_id, raw_input=raw_input, case_type=case_type)
        
        workflow = ["extractor", "researcher", "crafter", "reviewer"]
        
        for agent_name in workflow:
            agent = self.agents[agent_name]
            logger.info(f"🤖 [AGENT_{agent_name.upper()}] Ejecutando...")
            
            if not await agent.validate_input(state):
                logger.warning(f"⚠️ [AGENT_{agent_name.upper()}] Validación de entrada fallida. Intentando continuar...")
                state.review_notes.append(f"Validación omitida/fallida en {agent_name}")
                if agent_name == "extractor": break
                continue
            
            try:
                # Pasar el extra_prompt solo al Crafter
                if agent_name == "crafter" and extra_prompt:
                    output = await agent.execute(state, extra_prompt=extra_prompt)
                else:
                    output = await agent.execute(state)
                
                state = self._update_state(state, agent_name, output)
            except Exception as e:
                logger.error(f"❌ Error crítico en AGENTE_{agent_name.upper()}: {e}")
                state.review_notes.append(f"Fallo en ejecución de {agent_name}: {str(e)}")
                # Si el extractor o el crafter fallan, el flujo está comprometido
                if agent_name in ["extractor", "crafter"]:
                    logger.critical(f"🛑 [LEGAL_ORCHESTRATOR] Fallo en agente núcleo. Abortando flujo.")
                    break
                # Si falla el reviewer o researcher (RAG), podemos intentar seguir
                continue
            
        # Sincronizar con el puente de persistencia existente
        await self._persist_state(state)
        return state
    
    def _update_state(self, state: LegalCaseState, agent_name: str, output: dict) -> LegalCaseState:
        state.add_step(agent_name, output)
        if "facts" in output: state.facts = output["facts"]
        if "nombres" in output: state.nombres = output["nombres"]
        if "apellidos" in output: state.apellidos = output["apellidos"]
        if "documento" in output: state.documento = output["documento"]
        if "email" in output: state.email = output["email"]
        if "celular" in output: state.celular = output["celular"]
        if "direccion" in output: state.direccion = output["direccion"]
        if "legal_basis" in output: state.legal_basis = output["legal_basis"]
        if "citations_block" in output: state.citations_block = output["citations_block"]
        if "draft" in output: state.draft_document = output["draft"]
        if "package" in output: state.document_package = output["package"]
        if "review_status" in output: state.review_status = output["review_status"]
        if "score" in output: state.review_score = output["score"]
        if "notes" in output: state.review_notes.extend(output["notes"])
        return state
    
    async def _persist_state(self, state: LegalCaseState):
        radicado = f"LEGAL-{state.session_id[-4:].upper()}"
        await persistence_bridge.save_progress(state.session_id, radicado, {
            "tipo_solicitud": state.case_type.upper(),
            "estado": "REVISADO" if state.review_status == "approved" else "BORRADOR",
            "hechos_extraidos": "\n".join(state.facts),
            "borrador_proyeccion": state.draft_document,
            "review_score": getattr(state, "review_score", 0.5)
        })

legal_orchestrator = LegalOrchestrator()
