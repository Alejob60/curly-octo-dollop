import datetime
from typing import Dict, Any, List
from loguru import logger
from app.core.db_clients import mongo_db

class TelemetryAgent:
    """
    V62.9: Agente de Telemetría e Inteligencia de Productividad.
    Analiza flujos para identificar cuellos de botella y sugerir mejoras (REPAIR PLAN).
    """
    
    def __init__(self):
        self.mongo = mongo_db
    
    async def analyze_session_efficiency(self, session_id: str) -> dict:
        """Analiza un caso completo y retorna métricas + consejos"""
        if self.mongo is None: return {"error": "MongoDB offline"}
        
        try:
            # Obtener todos los pasos del flujo
            cursor = self.mongo["flow_telemetry"].find({"session_id": session_id}).sort("timestamp", 1)
            steps = await cursor.to_list(length=100)
            
            if not steps:
                return {"error": "No hay datos para analizar en esta sesión."}
            
            # Calcular métricas
            start_time = steps[0]["timestamp"]
            end_time = steps[-1]["timestamp"]
            total_duration = (end_time - start_time).total_seconds()
            
            # Identificar pasos lentos (>30 segundos)
            slow_steps = []
            for i in range(1, len(steps)):
                duration = (steps[i]["timestamp"] - steps[i-1]["timestamp"]).total_seconds()
                if duration > 30:
                    slow_steps.append({
                        "step": steps[i]["step_name"],
                        "duration_seconds": round(duration, 2)
                    })
            
            # Generar consejos IA (Heurísticos para el demo)
            suggestions = []
            if total_duration > 300:
                suggestions.append("⚡ El flujo excedió los 5 minutos. Optimice el RAG inicial.")
            
            if any("analyze" in step["step_name"] for step in slow_steps):
                suggestions.append("🧠 El análisis de IA inicial tomó demasiado tiempo. Considere usar modelos Flash.")
            
            if not any("finalize" in step["step_name"] for step in steps):
                suggestions.append("⚠️ La sesión aún no ha finalizado el sellado digital.")

            productivity_score = max(0, 100 - int(total_duration / 5))
            
            return {
                "session_id": session_id,
                "total_duration_seconds": round(total_duration, 2),
                "steps_count": len(steps),
                "slow_steps": slow_steps,
                "ai_suggestions": suggestions,
                "productivity_score": min(100, productivity_score),
                "status": "ANÁLISIS_COMPLETO"
            }
        except Exception as e:
            logger.error(f"❌ Error en TelemetryAgent: {e}")
            return {"error": str(e)}

    async def get_global_metrics(self, days: int = 7) -> dict:
        """Métricas agregadas para el dashboard de gobernanza"""
        if self.mongo is None: return {"error": "MongoDB offline"}
        
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$step_name",
                "avg_duration": {"$avg": "$processing_time"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"avg_duration": -1}}
        ]
        
        metrics = await self.mongo["flow_telemetry"].aggregate(pipeline).to_list(length=50)
        
        return {
            "period_days": days,
            "step_metrics": metrics,
            "generated_at": datetime.datetime.utcnow().isoformat()
        }

telemetry_agent = TelemetryAgent()
