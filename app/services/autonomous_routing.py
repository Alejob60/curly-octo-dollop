import json
import time
from typing import Dict, Any, Optional
from loguru import logger
from app.core.db_clients import redis_client, postgres_manager
from app.services.ledger_service import ledger_service
from sqlalchemy import update
from app.models.sql_models import CaseRegistry

class AutonomousRoutingEngine:
    """
    V55.1: Motor de Enrutamiento Autónomo para el Dashboard de Gobernanza.
    Clasifica casos en colas de ejecución basadas en confianza (AI Score) y urgencia.
    """
    
    QUEUES = {
        "EMERGENCY": "queue:emergency",
        "AUTO_APPROVE": "queue:auto_approve",
        "REVIEW": "queue:review",
        "HUMAN_ONLY": "queue:human_only"
    }

    def assign_queue(self, case_data: Dict[str, Any]) -> str:
        """
        Determina la cola correcta basada en el score de confianza y flags.
        """
        score = float(case_data.get("ai_score", 0.0))
        urgencia = case_data.get("urgencia_flag", "NORMAL")
        
        # 1. Prioridad Máxima: Emergencia Vital
        if urgencia == "VITAL":
            return self.QUEUES["EMERGENCY"]
        
        # 2. Alta Confianza (Elegible para Lote)
        if score >= 0.95:
            return self.QUEUES["AUTO_APPROVE"]
        
        # 3. Confianza Media (Requiere Revisión)
        if score >= 0.70:
            return self.QUEUES["REVIEW"]
        
        # 4. Baja Confianza o Fallo Crítico
        return self.QUEUES["HUMAN_ONLY"]

    async def route_and_persist(self, session_id: str, case_data: Dict[str, Any]):
        """
        Enruta el caso y actualiza Valkey (Colas de Gobernanza).
        La persistencia en PostgreSQL se delega al PersistenceBridge para evitar colisiones.
        """
        queue_name = self.assign_queue(case_data)
        radicado = case_data.get("radicado", f"GEN-{session_id[-4:]}")
        score = float(case_data.get("ai_score", 0.0))
        
        logger.info(f"🚦 [AUTONOMOUS_ROUTING] Enrutando {radicado} a {queue_name} (Score: {score:.2f})")

        # --- 🕵️ FORENSIC LOG: ROUTING ---
        await ledger_service.log_event(radicado, "ROUTING_ASSIGNED", {
            "session_id": session_id,
            "queue": queue_name,
            "confidence_score": score,
            "dependency_id": case_data.get("dependencia_id")
        })

        # 1. Persistencia en Valkey (Sorted Set por Tiempo/Prioridad)
        priority_score = time.time()
        await redis_client.zadd(queue_name, {session_id: priority_score})
        
        # Guardar metadatos extendidos en el estado de la sesión
        await redis_client.hset(f"pqrs:state:{session_id}", mapping={
            "routing_queue": queue_name,
            "confidence_score": str(score),
            "assigned_at": str(priority_score)
        })
        
        logger.success(f"🚦 [ROUTING] Caso encolado en {queue_name} correctamente.")

    async def get_queue_stats(self) -> Dict[str, int]:
        """Retorna el conteo de casos en cada cola."""
        stats = {}
        for key, q_name in self.QUEUES.items():
            count = await redis_client.zcard(q_name)
            stats[key] = count
        return stats

autonomous_router = AutonomousRoutingEngine()
