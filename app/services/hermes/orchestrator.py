from app.services.hermes.context_engine import hermes_context
from app.services.hermes.dynamic_routing import hermes_routing
from app.services.hermes.adaptive_rag import hermes_rag
from typing import Dict, Any, Tuple
from loguru import logger

class HermesOrchestrator:
    """
    Orquestador principal Hermes: coordina análisis, ruteo y grounding.
    """
    
    async def orchestrate(self, session_id: str, message: str, initial_dep: str) -> Dict[str, Any]:
        logger.info(f"🚀 [HERMES] Iniciando orquestación agéntica para sesión {session_id}")
        
        # 1. Análisis de contexto semántico jerárquico
        analysis = await hermes_context.analyze(message)
        
        # 2. Validación de enrutamiento y re-enrutamiento si es necesario
        final_dep_id, final_dep_name, was_rerouted = await hermes_routing.route_with_validation(
            message, initial_dep
        )
        
        # 3. Grounding adaptativo por tipo de problema
        citations = await hermes_rag.retrieve_grounding(
            message, final_dep_id, analysis.problem_type, analysis.confidence_score
        )
        
        return {
            "problem_type": analysis.problem_type,
            "primary_problem": analysis.primary_problem,
            "urgency": analysis.urgency_level,
            "dependency_id": final_dep_id,
            "dependency_name": final_dep_name,
            "was_rerouted": was_rerouted,
            "citations": citations,
            "context_elements": analysis.context_elements
        }

hermes_orchestrator = HermesOrchestrator()
