from fastapi import APIRouter, HTTPException, Body, Request
from typing import Any, Optional, Dict
from pydantic import BaseModel
from app.services.pqrs_manager import pqrs_manager
from app.services.pre_render_validator import PreRenderValidator
from app.services.privacy_shield_service import privacy_shield
from app.services.phase_orchestrator import phase_guard, Phase
from app.services.ledger_service import ledger_service
from app.core.db_clients import redis_client, postgres_manager
from app.core.config import settings
from loguru import logger
import json
import hashlib
import os
import datetime
import traceback
import base64

router = APIRouter()

STATE_PREFIX = "pqrs:state:"

class FinalizeRequest(BaseModel):
    session_id: str
    audit_draft: Optional[str] = None

@router.post("/register-consent")
async def register_consent(
    request: Request,
    session_id: str = Body(..., embed=True),
    consent_type: str = Body(..., embed=True)
):
    try:
        client_ip = request.client.host if request.client else "unknown"
        result = await pqrs_manager.register_citizen_consent(session_id, consent_type, client_ip)
        return result
    except Exception as e:
        logger.error(f"❌ Error en Consentimiento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def analyze_pqrs(
    session_id: str = Body(..., embed=True),
    message: str = Body(..., embed=True)
):
    try:
        logger.info(f"🔍 [IN_ANALYZE] session={session_id} | msg={message[:50]}...")
        result = await pqrs_manager.analyze_initial_message(session_id, message)
        logger.info(f"📤 [OUT_ANALYZE] response={json.dumps(result, indent=2)}")
        return result
    except Exception as e:
        logger.error(f"🔥 Fallo en Análisis Primario: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

class SlotUpdateRequest(BaseModel):
    session_id: str
    current_phase: Optional[str] = None
    slots: Optional[Dict[str, Any]] = None

@router.post("/update-slot")
async def update_pqrs_slot(request: SlotUpdateRequest):
    session_id = request.session_id
    state_key = f"{STATE_PREFIX}{session_id}"
    try:
        logger.info(f"📥 [IN_UPDATE-SLOT] session={session_id} | phase={request.current_phase} | slots={request.slots}")
        
        # 🔥 FIX V63.8: Auto-confirmación Robusta
        session_state = await redis_client.hgetall(state_key)
        # Redis ya retorna strings (decode_responses=True)
        current_phase = session_state.get("current_phase", "fase_1_identidad")
        
        slots = request.slots or {}
        
        # Persistir datos si vienen en request.slots
        if slots:
            mapping = {k: (json.dumps(v) if isinstance(v, (list, dict)) else str(v)) for k, v in slots.items() if v is not None}
            if mapping:
                await redis_client.hset(state_key, mapping=mapping)

        # Manejar flags explícitos (pueden venir dentro de slots)
        auth_flag = slots.get("autorizacion_datos")
        if auth_flag is not None:
            await redis_client.hset(state_key, "autorizacion_datos", "True" if auth_flag else "False")
        
        # 'confirmed' es de la Fase 3 (Evidencia)
        if slots.get("confirmed"):
            await redis_client.hset(state_key, "confirmed", "true")
            
        # 'confirmado' es de la Fase 4 (Revisión Final)
        if slots.get("confirmado"):
            await redis_client.hset(state_key, "confirmado", "true")
            await redis_client.hset(state_key, "confirmed_at", datetime.datetime.utcnow().isoformat())

        # Si estamos en fase 4 (Revisión) y ya confirma final, disparamos generación
        is_confirmed_final = (await redis_client.hget(state_key, "confirmado")) in ["true", b"true"]
        
        if current_phase == "fase_4_evidencia" and is_confirmed_final:
             logger.success(f"🚀 [PHASE_4_COMPLETE] Iniciando generación para {session_id}")
             
             # Card de progreso INICIAL (señal para el frontend)
             progress_response = {
                "type": "card",
                "cardType": "ProcessingCard",
                "session_id": session_id,
                "submessage": "Por favor espere mientras el Magistrado valida su expediente...",
                "progress": 0,
                "steps": [
                    "⏳ Rehidratando información...",
                    "⏳ Auditoría jurídica IA...",
                    "⏳ Generando memoriales...",
                    "⏳ Sellando en bóveda inmutable..."
                ]
             }
             
             # Ejecutar el TRABAJO REAL en background
             import asyncio
             asyncio.create_task(pqrs_manager.finalize_pqrs(session_id))
             
             logger.info(f"📤 [OUT_UPDATE-SLOT] returning ProcessingCard and starting real work in background")
             return progress_response

        instruction = await pqrs_manager.get_next_ui_instruction(session_id)
        logger.info(f"📤 [OUT_UPDATE-SLOT] response={json.dumps(instruction, indent=2)}")
        return instruction
    except Exception as e:
        logger.error(f"🔥 [API_ERROR] Error en Update Slot: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress/{session_id}")
async def get_progress(session_id: str):
    """Endpoint para polling: frontend consulta estado de generación"""
    try:
        # 1. Verificar error
        error = await redis_client.get(f"progress:{session_id}:error")
        if error:
            return {"status": "error", "progress": 0, "message": str(error)}
        
        # 2. Verificar completado
        is_complete = await redis_client.get(f"progress:{session_id}:complete")
        if is_complete in ["true", b"true", "1"]:
            final_data = await redis_client.get(f"progress:{session_id}:final")
            if final_data:
                return {
                    "status": "complete",
                    "progress": 100,
                    "message": "✅ Expediente generado exitosamente",
                    "data": json.loads(final_data) if isinstance(final_data, str) else json.loads(final_data.decode())
                }
        
        # 3. Retornar progreso actual
        progress_raw = await redis_client.get(f"progress:{session_id}")
        if progress_raw:
            return json.loads(progress_raw) if isinstance(progress_raw, str) else json.loads(progress_raw.decode())
        
        return {"status": "queued", "progress": 0, "message": "⏳ En cola..."}
    except Exception as e:
        logger.error(f"❌ Error en get_progress: {e}")
        return {"status": "error", "progress": 0, "message": str(e)}

@router.get("/session/{session_id}")
async def recover_session(session_id: str):
    """
    Recuperar estado completo de una sesión existente (V64.2).
    Retorna: cardType, phase, datos, documentos (si existen)
    """
    try:
        state_key = f"{STATE_PREFIX}{session_id}"
        state = await redis_client.hgetall(state_key)
        
        # 1. Caso: Sesión completada (Busca en cache final)
        is_complete = await redis_client.get(f"progress:{session_id}:complete")
        if is_complete in ["true", b"true", "1"]:
            final = await redis_client.get(f"progress:{session_id}:final")
            if final:
                final_data = json.loads(final) if isinstance(final, str) else json.loads(final.decode())
                return {
                    "status": "completed",
                    "session_id": session_id,
                    "cardType": "SuccessCard",
                    "data": final_data,
                    "documents": final_data.get("documents", [])
                }

        if not state:
            return {"status": "not_found", "message": "Sesión expirada o no existe"}
        
        # 2. Parsear estado activo desde Redis
        parsed = {
            (k.decode() if isinstance(k, bytes) else k): 
            (v.decode() if isinstance(v, bytes) else v) 
            for k, v in state.items()
        }
        
        # Determinar fase y cardType
        current_phase = parsed.get("current_phase", "fase_1_identidad")
        
        # Mapeo fase → cardType
        card_map = {
            "fase_1_identidad": "IdentityCard",
            "fase_2_triaje": "ContactCard", 
            "fase_3_analisis": "EvidenceAndLegalCard",
            "fase_4_evidencia": "ConfirmationCard",
            "fase_5_confirmacion": "SuccessCard"
        }
        
        # Verificar confirmación para saltar a procesamiento si es necesario
        is_confirmed_final = parsed.get("confirmado") in ["true", b"true", "1"]
        card_type = card_map.get(current_phase, "IdentityCard")
        
        if current_phase == "fase_4_evidencia" and is_confirmed_final:
            card_type = "ProcessingCard"

        return {
            "status": "active",
            "session_id": session_id,
            "cardType": card_type,
            "current_phase": current_phase,
            "data": parsed
        }
        
    except Exception as e:
        logger.error(f"❌ Error recuperando sesión {session_id}: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/finalize")
async def finalize_pqrs(request: FinalizeRequest):
    """
    HU 3.4: Cierre forense (V64.2). 
    Sincroniza con el proceso en background o lo inicia si no existe.
    """
    session_id = request.session_id
    try:
        # Verificar si ya completó en background para evitar doble trabajo
        is_complete = await redis_client.get(f"progress:{session_id}:complete")
        if is_complete in ["true", b"true"]:
            progress_raw = await redis_client.get(f"progress:{session_id}")
            if progress_raw:
                prog_json = json.loads(progress_raw)
                if "data" in prog_json:
                    logger.info(f"🏁 [FINALIZE] Retornando resultado ya generado para {session_id}")
                    return prog_json["data"]
        
        # Si no se ha hecho o está a medias, lo ejecutamos
        # Esto sirve de fallback si el background task falló en iniciar
        return await pqrs_manager.finalize_pqrs(session_id)

    except Exception as e:
        logger.error(f"🔥 [CRITICAL_FINALIZE] {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Error interno durante el sellado.",
                "user_messages": [{
                    "type": "error",
                    "title": "Fallo en el Sellado Digital",
                    "body": f"Ocurrió un problema técnico: {str(e)}."
                }]
            }
        )
