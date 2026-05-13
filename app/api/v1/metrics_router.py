from fastapi import APIRouter
from app.core.db_clients import mongo_manager, redis_client
from loguru import logger
import time
from datetime import datetime

router = APIRouter(prefix="/api/v1/metrics", tags=["Monitoring & Analytics"])

@router.get("/pipeline")
async def get_pipeline_metrics():
    """
    💎 [V65.14] Métricas en tiempo real del motor Diamond.
    Expone KPIs de la cola batch y salud del sistema.
    """
    try:
        db = mongo_manager.get_db()
        if db is None: return {"error": "MongoDB Offline"}

        # 1. Estado de la Cola
        pending = await db["pqrs_pending"].count_documents({"status": "PENDING"})
        processing = await db["pqrs_pending"].count_documents({"status": "PROCESSING"})
        completed = await db["pqrs_pending"].count_documents({"status": "COMPLETED"})
        failed_dlq = await db["pqrs_dlq"].count_documents({})

        # 2. Rendimiento (Últimos 100)
        cursor = db["pqrs_pending"].find({"status": "COMPLETED"}).sort("finished_at", -1).limit(100)
        docs = await cursor.to_list(100)
        
        avg_confidence = 0.0
        if docs:
            avg_confidence = sum(d.get("confidence_score", 0.0) for d in docs) / len(docs)

        # 3. Salud de IA (Vertex)
        vertex_status = "HEALTHY"
        # Podríamos chequear Redis para ver si hay flags de error recientes
        last_error = await redis_client.get("vertex:last_error")
        if last_error: vertex_status = "DEGRADED"

        return {
            "queue": {
                "total_backlog": pending + processing + completed + failed_dlq,
                "pending": pending,
                "processing": processing,
                "completed": completed,
                "failed": failed_dlq
            },
            "performance": {
                "avg_confidence": round(avg_confidence, 2),
                "success_rate": round((completed / (completed + failed_dlq) * 100), 2) if (completed + failed_dlq) > 0 else 100,
                "vertex_status": vertex_status
            },
            "system": {
                "version": "V65.14",
                "timestamp": time.time()
            }
        }
    except Exception as e:
        logger.error(f"❌ Error recuperando métricas: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/pipeline/reviews")
async def get_human_reviews():
    """
    💎 [V65.14] Recupera casos bloqueados por el Guardián.
    """
    try:
        db = mongo_manager.get_db()
        # Buscamos en la colección de revisión humana
        cursor = db["pqrs_human_review"].find({"status": "PENDING"}).sort("created_at", -1)
        items = await cursor.to_list(50)
        
        for item in items:
            item["_id"] = str(item["_id"])
            if "created_at" in item and isinstance(item["created_at"], float):
                item["created_at"] = datetime.fromtimestamp(item["created_at"]).isoformat()

        return {"items": items}
    except Exception as e:
        logger.error(f"❌ Error en bandeja de revisión: {e}")
        return {"items": []}
