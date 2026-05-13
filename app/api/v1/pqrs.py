from fastapi import APIRouter, HTTPException, Body, Request
from typing import Any, Optional, Dict
from pydantic import BaseModel
from loguru import logger
import json
import datetime
from sse_starlette.sse import EventSourceResponse

from app.services.pqrs_manager import pqrs_manager
from app.services.orchestrator import orchestrator
from app.core.db_clients import redis_client

router = APIRouter()

STATE_PREFIX = "pqrs:state:"

class FinalizeRequest(BaseModel):
    session_id: str

class SlotUpdateRequest(BaseModel):
    session_id: str
    current_phase: Optional[str] = None
    slots: Optional[Dict[str, Any]] = None

@router.post("/register-consent")
async def register_consent(
    request: Request,
    session_id: str = Body(..., embed=True),
    consent_type: str = Body(..., embed=True)
):
    """V65.0: Registro de consentimiento (Habeas Data)"""
    try:
        client_ip = request.client.host if request.client else "unknown"
        return await pqrs_manager.register_citizen_consent(session_id, consent_type, client_ip)
    except Exception as e:
        logger.error(f"❌ Error en Consentimiento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_pqrs(
    session_id: str = Body(..., embed=True),
    message: str = Body(..., embed=True)
):
    """V65.0: Análisis inicial determinista"""
    try:
        logger.info(f"🔍 [V65.0] [IN_ANALYZE] session={session_id}")
        
        # Limpiar estados previos
        await redis_client.delete(f"progress:{session_id}")
        await redis_client.delete(f"progress:{session_id}:error")
        
        # Iniciar flujo
        return await pqrs_manager.analyze_initial_message(session_id, message)
    except Exception as e:
        logger.error(f"🔥 Fallo en Analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update-slot")
async def update_pqrs_slot(request: SlotUpdateRequest):
    """💎 [V65.14] Sincronización de datos con Deep Logging"""
    try:
        session_id = request.session_id
        state_key = f"{STATE_PREFIX}{session_id}"
        
        slots = request.slots or {}
        if slots:
            # 🔍 LOG SLOTS RECEIVED
            logger.debug(f"📥 [SLOTS_RECV] session={session_id} | data={json.dumps(slots)}")
            
            mapping = {k: (json.dumps(v) if isinstance(v, (list, dict)) else str(v)) for k, v in slots.items() if v is not None}
            if mapping:
                await redis_client.hset(state_key, mapping=mapping)

        # 👁️ [GODS_EYE]
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "phase": "fase_2_triaje",
            "service": "pqrs_manager",
            "action": "update_slot",
            "payload_json": slots, # 🔍 FULL JSON IN LOG
            "persistence": {"redis_updated": True, "fields_synced": len(slots)}
        }
        logger.info(f"👁️ [PHASE_2_UPDATE_LOG] {json.dumps(log_entry, indent=2)}")

        # 🛡️ CHECK FINAL CONFIRMATION (Resilient Boolean)
        conf_raw = slots.get("confirmado") or slots.get("confirmed")
        is_confirmed_final = str(conf_raw).lower() in ["true", "1", "yes", "t", "confirmado"]
        
        if is_confirmed_final:
             logger.success(f"🚀 [AUTO_FINALIZE_TRIGGER] session={session_id}")
             try:
                result = await pqrs_manager.finalize_pqrs(session_id)
                logger.info(f"🏁 [FINALIZE_RESULT] session={session_id} | data={json.dumps(result, indent=2)}")
                return {"type": "card", "cardType": "SuccessCard", "data": result}
             except Exception as e:
                logger.error(f"🔥 [CRITICAL_FINALIZE] {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=str(e))

        # Recuperar estado actual para decidir siguiente instrucción
        raw_state = await redis_client.hgetall(state_key)
        state_data = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in raw_state.items()}
        
        instruction = await pqrs_manager.get_next_ui_instruction(session_id, state_data)
        logger.debug(f"📤 [NEXT_UI_INS] session={session_id} | card={instruction.get('cardType')}")
        
        return instruction
    except Exception as e:
        logger.error(f"🔥 [API_ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/stream")
async def stream_progress(session_id: str):
    """💎 MÓDULO 5: SSE STREAMING (V65.8)"""
    return EventSourceResponse(orchestrator.sse_event_generator(session_id))

@router.get("/{session_id}/progress")
async def get_progress_v2(session_id: str):
    """Endpoint para polling del frontend (Aplanado V65.4)"""
    try:
        progress_key = f"progress:{session_id}"
        progress_raw = await redis_client.get(progress_key)
        
        if not progress_raw:
            return {"phase": "unknown", "message": "Iniciando...", "progress": 0}
        
        data = json.loads(progress_raw)
        is_complete = data.get("status") == "complete" or data.get("progress") == 100
        
        return {
            **data,
            "transition": is_complete
        }
    except Exception as e:
        logger.error(f"❌ Error polling: {e}")
        return {"phase": "error", "message": str(e), "progress": 0}

@router.get("/progress/{session_id}")
async def get_progress(session_id: str):
    """V65.0: Polling minimalista (Aplanado V65.4)"""
    try:
        error = await redis_client.get(f"progress:{session_id}:error")
        if error: return {"status": "error", "message": str(error)}
        
        progress_raw = await redis_client.get(f"progress:{session_id}")
        if progress_raw:
            data = json.loads(progress_raw)
            if data.get("status") == "complete" or data.get("progress") == 100:
                return { **data, "status": "complete", "transition": True }
            return data
        
        return {"status": "idle", "progress": 0}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/finalize")
async def finalize_pqrs(request: FinalizeRequest):
    """V65.0: Cierre determinista"""
    try:
        return await pqrs_manager.finalize_pqrs(request.session_id)
    except Exception as e:
        logger.error(f"🔥 [CRITICAL_FINALIZE] {e}")
        raise HTTPException(status_code=500, detail=str(e))
