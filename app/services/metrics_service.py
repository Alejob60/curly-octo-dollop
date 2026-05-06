import datetime
import json
from app.core.db_clients import mongo_db
from loguru import logger
from typing import Dict, Any

class MetricsService:
    """
    QA-5.4: Dashboard de métricas de determinismo y calidad legal.
    """
    
    def __init__(self):
        self.collection = mongo_db.quality_metrics

    async def log_extraction_metric(self, session_id: str, method: str, success: bool, data: dict):
        """Registra la consistencia de la extracción de datos."""
        metric = {
            "timestamp": datetime.datetime.utcnow(),
            "session_id": session_id,
            "type": "extraction",
            "method": method, # 'regex' o 'ia'
            "success": success,
            "fields_captured": list(data.keys())
        }
        await self.collection.insert_one(metric)

    async def log_grounding_metric(self, radicado: str, ratio: float, invalid_citations: list):
        """Registra la precisión legal de los documentos generados."""
        metric = {
            "timestamp": datetime.datetime.utcnow(),
            "radicado": radicado,
            "type": "grounding",
            "ratio": ratio,
            "is_valid": ratio >= 0.95,
            "invalid_count": len(invalid_citations)
        }
        await self.collection.insert_one(metric)
        logger.info(f"📊 Métrica Grounding Guardada: {ratio*100}% [Radicado: {radicado}]")

    async def get_system_health(self) -> Dict[str, Any]:
        """Calcula el score de salud general del sistema."""
        pipeline = [
            {"$group": {
                "_id": "$type",
                "avg_success": {"$avg": {"$cond": [{"$eq": ["$is_valid", True]}, 1, 0]}},
                "count": {"$sum": 1}
            }}
        ]
        results = await self.collection.aggregate(pipeline).to_list(length=10)
        return {r["_id"]: r for r in results}

metrics_service = MetricsService()
