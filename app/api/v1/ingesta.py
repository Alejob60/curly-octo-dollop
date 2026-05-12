from fastapi import APIRouter, HTTPException, Body, Request, Header, BackgroundTasks
from typing import Any, Optional, Dict
from pydantic import ValidationError
from loguru import logger
import uuid
import json

from app.models.pqrs_input import PQRSInputSchema
from app.services.idempotency import check_idempotency, mark_processed, unmark_processed
from app.services.queue_processor import enqueue_pqrs

router = APIRouter()

from app.services.priority_calculator import calculate_priority_score
from app.services.sse_manager import sse_manager
from starlette.responses import StreamingResponse

# ... (imports)

@router.post("/submit", status_code=202)
async def submit_pqrs(
    payload: PQRSInputSchema,
    background_tasks: BackgroundTasks,
    x_source: str = Header("api", alias="X-Source"),
    x_idempotency: str = Header(None, alias="X-Idempotency-Key")
):
    """
    💎 [V65.13] Endpoint Unificado de Ingesta Priorizada.
    """
    try:
        # 1. Normalización e Idempotencia
        source = payload.source or x_source.lower()
        if not x_idempotency and not payload.idempotency_key:
            seed = f"{payload.asunto}-{payload.identificacion or str(uuid.uuid4())}"
            idem_key = str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
        else:
            idem_key = payload.idempotency_key or x_idempotency

        if await check_idempotency(idem_key):
            return {"status": "DUPLICATE", "idempotency_key": idem_key}
        
        await mark_processed(idem_key)

        # 2. Cálculo de Prioridad (V65.14)
        priority = calculate_priority_score(payload.model_dump())

        # 3. Encolado Asíncrono
        background_tasks.add_task(enqueue_pqrs, payload.model_dump(), source, idem_key, priority)
        
        logger.info(f"✅ [PQRS_ACCEPTED] ID: {idem_key} | Prioridad: {priority['level']}")
        
        return {
            "status": "ACCEPTED",
            "idempotency_key": idem_key,
            "priority_level": priority["level"],
            "estimated_sla_hours": priority["sla_hours"],
            "tracking_url": f"/api/v1/pqrs/stream/{idem_key}"
        }

    except Exception as e:
        logger.error(f"🔥 Fallo en Ingesta: {e}")
        if 'idem_key' in locals(): await unmark_processed(idem_key)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream/{tracking_id}")
async def stream_progress(request: Request, tracking_id: str):
    """💎 [V65.14] SSE Streaming para seguimiento de colas."""
    return StreamingResponse(
        sse_manager.event_generator(request, tracking_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/queue/stats")
async def get_queue_stats():
    """Métrica rápida de la cola de procesamiento."""
    try:
        from app.core.db_clients import mongo_manager
        db = mongo_manager.get_db()
        pending = await db["pqrs_pending"].count_documents({"status": "PENDING"})
        processing = await db["pqrs_pending"].count_documents({"status": "PROCESSING"})
        completed = await db["pqrs_pending"].count_documents({"status": "COMPLETED"})
        failed = await db["pqrs_dlq"].count_documents({})
        
        return {
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed_dlq": failed
        }
    except Exception as e:
        return {"error": str(e)}
