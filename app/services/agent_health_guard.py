import httpx, json, logging, os
from datetime import datetime, timedelta
from typing import Literal, Optional, Tuple, List
from pydantic import BaseModel, ValidationError
from app.models.legal_models import StrictLegalOutput
from app.core.config import settings
from loguru import logger

class HealthDecision(BaseModel):
    decision: Literal["USE_CALI_LEX", "USE_VERTEX_FALLBACK", "BLOCK_AND_REVIEW"]
    reason: str
    confidence: float
    route_metadata: dict
    timestamp: str

class AgentHealthGuard:
    """
    🛡️ [V65.14 Diamond] Guardián de Salud y Fallback.
    Decide la ruta de procesamiento más segura para cada PQRSD.
    """
    
    def __init__(self):
        self._health_cache = {}
        self.threshold = settings.MIN_CONFIDENCE_THRESHOLD
        self.placeholders = ["123456789", "equipo técnico", "50 personas", "cc 123456789", "por definir"]

    async def check_agent_health(self) -> bool:
        """Verifica si el motor de IA principal responde."""
        now = datetime.now()
        if "last_check" in self._health_cache:
            if now - self._health_cache["last_check"] < timedelta(seconds=60):
                return self._health_cache["is_healthy"]
        
        # En este entorno, el "agente" es nuestro propio motor Vertex
        # El health check valida la conectividad con Google Cloud / AI Studio
        try:
            from app.core.vertex_client import vertex_client
            # Llamada mínima de validación
            await vertex_client.generate_content(["ping"])
            is_healthy = True
        except Exception as e:
            logger.warning(f"⚠️ [HEALTH_CHECK] Motor de IA no responde: {e}")
            is_healthy = False
            
        self._health_cache.update({"last_check": now, "is_healthy": is_healthy})
        return is_healthy

    def validate_output_quality(self, output: dict) -> Tuple[bool, List[str]]:
        """Nivel 2: Validar calidad técnica de la respuesta."""
        errors = []
        
        # 1. Schema Pydantic
        try:
            StrictLegalOutput.model_validate(output)
        except ValidationError as e:
            errors.append(f"Esquema inválido: {e.error_count()} errores")
        
        # 2. Confianza
        confidence = output.get("auditoria", {}).get("confidence_score", 0.0)
        # Si no viene en auditoria, buscamos en el root (V65.12 compat)
        if confidence == 0.0: confidence = output.get("confidence", 0.0)
        
        if confidence < self.threshold:
            errors.append(f"Confianza baja: {confidence:.2f} < {self.threshold}")
            
        # 3. Placeholders
        raw_text = json.dumps(output, ensure_ascii=False).lower()
        found = [ph for ph in self.placeholders if ph in raw_text]
        if found:
            errors.append(f"Placeholders detectados: {found}")
            
        return len(errors) == 0, errors

    async def decide_route(self, payload: dict, ai_response: Optional[dict] = None) -> HealthDecision:
        """Evalúa la matriz de decisión y retorna la ruta óptima."""
        
        # NIVEL 1: Salud del Motor
        is_healthy = await self.check_agent_health()
        if not is_healthy:
            return HealthDecision(
                decision="BLOCK_AND_REVIEW",
                reason="ia_engine_unavailable",
                confidence=0.0,
                route_metadata={"health": "FAIL"},
                timestamp=datetime.now().isoformat()
            )

        if ai_response is None:
             return HealthDecision(
                decision="BLOCK_AND_REVIEW",
                reason="no_ai_response_provided",
                confidence=0.0,
                route_metadata={"health": "OK"},
                timestamp=datetime.now().isoformat()
            )

        # NIVEL 2: Calidad
        is_valid, errors = self.validate_output_quality(ai_response)
        if is_valid:
            return HealthDecision(
                decision="USE_CALI_LEX",
                reason="quality_certified",
                confidence=ai_response.get("confidence", 1.0),
                route_metadata={"health": "OK", "validation": "PASS"},
                timestamp=datetime.now().isoformat()
            )
            
        # NIVEL 3: Fallback (Vertex Strict)
        logger.warning(f"⚠️ [DECISION] Calidad insuficiente: {errors}. Evaluando Fallback...")
        return HealthDecision(
            decision="BLOCK_AND_REVIEW", # Por defecto bloqueamos en producción crítica
            reason=f"quality_fail: {'; '.join(errors)}",
            confidence=0.0,
            route_metadata={"health": "OK", "validation": "FAIL"},
            timestamp=datetime.now().isoformat()
        )

agent_health_guard = AgentHealthGuard()
