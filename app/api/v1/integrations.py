from fastapi import APIRouter, HTTPException, Body
from app.models.sql_models import IntegrationConnector
from app.core.db_clients import postgres_manager
from app.integrations.sync_engine import sync_engine
from sqlalchemy import select, desc
from typing import List, Any
import datetime
import hashlib
from loguru import logger

router = APIRouter(prefix="/integrations", tags=["Interoperabilidad PR-01"])

@router.get("/connectors")
async def list_connectors():
    """Lista todos los conectores legacy configurados."""
    async with postgres_manager.get_session() as session:
        result = await session.execute(select(IntegrationConnector).order_by(desc(IntegrationConnector.created_at)))
        return result.scalars().all()

@router.post("/connectors")
async def create_connector(payload: dict = Body(...)):
    """Crea un nuevo conector institucional."""
    async with postgres_manager.get_session() as session:
        new_conn = IntegrationConnector(
            id=payload.get("id") or f"conn_{datetime.datetime.utcnow().strftime('%H%M%S')}",
            name=payload["name"],
            system_type=payload["system_type"],
            protocol=payload["protocol"],
            config=payload["config"],
            field_mapping=payload.get("field_mapping", {}),
            status="active"
        )
        session.add(new_conn)
        await session.commit()
        return new_conn

@router.post("/connectors/{connector_id}/sync")
async def trigger_manual_sync(connector_id: str):
    """Dispara una sincronización manual inmediata."""
    await sync_engine.sync_connector(connector_id)
    return {"status": "triggered"}

@router.get("/connectors/{connector_id}/health")
async def check_connector_health(connector_id: str):
    """Verifica si el sistema legacy responde."""
    async with postgres_manager.get_session() as session:
        connector = await session.get(IntegrationConnector, connector_id)
        if not connector: raise HTTPException(404, "Conector no encontrado")
        return {"id": connector_id, "health": connector.health_status, "last_error": connector.last_error}

@router.post("/omnichannel/ingest")
async def omnichannel_ingest(
    payload: dict = Body(...)
):
    """
    SPRINT 2 (PR-01): Ingestión Omnicanal.
    Recibe peticiones de WhatsApp (Twilio/Meta), Email (GCP Relay) o Portales.
    """
    source = payload.get("source", "external") # whatsapp | email | portal
    message = payload.get("message")
    sender_id = payload.get("sender_id") # Numero o Correo
    
    if not message or not sender_id:
        raise HTTPException(status_code=400, detail="Mensaje y Remitente obligatorios")

    session_id = f"omni-{source}-{hashlib.md5(sender_id.encode()).hexdigest()[:8]}"
    
    logger.info(f"📱 [OMNICHANNEL] Ingestión desde {source}: {sender_id}")
    
    # Inyectamos directamente al motor de análisis
    from app.services.pqrs_manager import pqrs_manager
    instruction = await pqrs_manager.analyze_initial_message(session_id, message)
    
    return {
        "status": "success",
        "session_id": session_id,
        "source": source,
        "ia_instruction": instruction
    }
