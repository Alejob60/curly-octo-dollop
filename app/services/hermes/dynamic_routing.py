from app.services.hermes.context_engine import hermes_context, ContextAnalysis
from typing import Tuple, List, Dict
from loguru import logger

DEPENDENCY_NAMES = {
    "4146": "Secretaría de Infraestructura",
    "4135": "Secretaría de Salud Pública",
    "4152": "Secretaría de Movilidad",
    "2201": "Secretaría de Educación",
    "4131": "Secretaría General"
}

class DynamicRoutingLayer:
    """
    Capa de enrutamiento dinámico con validación de consistencia.
    """
    
    async def route_with_validation(self, raw_input: str, initial_dependency: str) -> Tuple[str, str, bool]:
        # Paso 1: Análisis de contexto semántico
        analysis = await hermes_context.analyze(raw_input)
        
        logger.info(f"🧠 [HERMES_ROUTING] Contexto: {analysis.primary_problem} (Confianza: {analysis.confidence_score:.2f})")
        
        # Paso 2: Validar consistencia
        # Si la inicial no está en las sugeridas por contexto, y tenemos confianza alta en el contexto
        is_consistent = initial_dependency in analysis.suggested_dependencies
        
        if is_consistent:
            logger.info(f"✅ [ROUTING] Consistencia validada: {initial_dependency} (Sugerida por contexto)")
            return initial_dependency, DEPENDENCY_NAMES.get(initial_dependency, "Secretaría General"), False
            
        if analysis.confidence_score < 0.6:
            logger.info(f"⚠️ [ROUTING] Confianza baja ({analysis.confidence_score:.2f}): Manteniendo dependencia inicial {initial_dependency}")
            return initial_dependency, DEPENDENCY_NAMES.get(initial_dependency, "Secretaría General"), False
        
        # Paso 3: Re-enrutamiento automático
        target_dependency = analysis.suggested_dependencies[0]
        dep_name = DEPENDENCY_NAMES.get(target_dependency, "Secretaría General")
        
        logger.warning(f"🔄 [RE-ROUTING] Inconsistencia detectada.")
        logger.warning(f"   • Inicial: {initial_dependency}")
        logger.warning(f"   • Sugerido: {target_dependency} ({dep_name})")
        
        return target_dependency, dep_name, True

hermes_routing = DynamicRoutingLayer()
