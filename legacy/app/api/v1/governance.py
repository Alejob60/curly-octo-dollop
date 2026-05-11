from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List
import json
import asyncio
from loguru import logger
from datetime import datetime
import random

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")

manager = ConnectionManager()

@router.get("/infra-status")
async def get_infra_status():
    """
    Expose status of KMS and Bucket Lock for the Governance Dashboard.
    """
    from app.services.gcp_storage_service import immutable_storage_service
    from app.services.signer import signer_service
    from app.services.ledger_service import ledger_service
    
    return {
        "kms": {
            "status": "ACTIVE" if signer_service.client else "LOCAL_MODE",
            "provider": "GCP KMS",
            "key_id": signer_service.key or "None"
        },
        "storage": {
            "bucket": immutable_storage_service.bucket_name or "None",
            "retention_policy": "ACTIVE (20 years)" if immutable_storage_service.bucket else "INACTIVE",
            "worm_enabled": True if immutable_storage_service.bucket else False
        },
        "ledger": {
            "provider": ledger_service.provider,
            "status": "CONNECTED" if (ledger_service.client or ledger_service.provider == "gcp") else "DEGRADED"
        }
    }

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Enviar estado inicial
        initial_metrics = {
            "type": "INITIAL_METRICS",
            "confidence": 94,
            "delayDaysPrevented": 124,
            "fiscalSavings": 450,
            "alerts": 3,
            "statusLane": "green"
        }
        await websocket.send_text(json.dumps(initial_metrics))
        
        while True:
            # Simular eventos de monitoreo para la demo (ST-23)
            # En producción esto reaccionaría a eventos reales de Redis/DB
            await asyncio.sleep(10) 
            
            event = {
                "type": "LIVE_ACTIVITY",
                "radicado": f"CALI-2026-WOW-{random.randint(1000, 9999)}",
                "message": "Procesado exitosamente por IA",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_text(json.dumps(event))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from governance stream")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@router.post("/broadcast-event")
async def broadcast_governance_event(event: dict):
    """
    Permite al backend emitir eventos al dashboard de gobernanza.
    """
    await manager.broadcast(json.dumps(event))
    return {"status": "broadcasted"}
