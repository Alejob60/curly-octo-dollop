from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.conversation_manager import conversation_manager
from loguru import logger
import uuid

router = APIRouter()

from app.repositories.radicacion_repository import radicado_repo
from app.services.ledger_service import ledger_service
from app.services.integration_security_service import integration_security_service
import datetime

from app.services.governance_service import governance_service
from app.core.db_clients import AsyncSessionLocal
import hashlib

@router.post("/confirm/{session_id}")
async def confirm_chat_radication(session_id: str):
    """
    CHAT-06: Cierre de conversación y radicación oficial con Gobernanza.
    """
    try:
        # 1. Transformar conversación en JSON estructurado
        final_data = await conversation_manager.distill_conversation(session_id)
        
        # 2. Generar Radicado y Hash
        radicado_id = f"OP-CHAT-{uuid.uuid4().hex[:6].upper()}"
        chat_history = await conversation_manager.get_history(session_id)
        chat_content = json.dumps(chat_history)
        hash_seguridad = hashlib.sha256(chat_content.encode()).hexdigest()
        
        # 3. REAL-07: Sellar Transcripción en Ledger (Inmutabilidad)
        await ledger_service.log_event(
            radicado_id,
            "CHAT_CONVERSATION_SEALED",
            {"history_preview": chat_content[:500], "full_hash": hash_seguridad}
        )
        
        # 4. Gobernanza Legal (PostgreSQL)
        try:
            dep_id = int(final_data.get("suggested_dependency_id") or 4112)
            type_id = 1 # Default Petición General para Chat
        except:
            dep_id = 4112
            type_id = 1

        async with AsyncSessionLocal() as session:
            async with session.begin():
                new_radicado = await governance_service.register_radicado(session, {
                    "codigo_radicado": radicado_id,
                    "hash_seguridad": hash_seguridad,
                    "id_usuario": final_data.get("citizen_id", "ANONYMOUS_CHAT"),
                    "id_dependencia": dep_id,
                    "id_tipo_pqrs": type_id
                })
                
                # FLOW-02: Forzar estado de revisión humana
                new_radicado.estado_actual = "PENDIENTE_VISTO_BUENO"
                
                # Registrar en tabla de asignaciones para el Dashboard del Abogado
                from app.models.sql_models import Asignacion
                asignacion = Asignacion(
                    radicado_id=new_radicado.id,
                    funcionario_id=dep_id, # Placeholder: en producción usa el ID del abogado asignado
                    nivel_complejidad="MEDIO",
                    sugerencia_ia_json=json.dumps(final_data),
                    estado_revision="SUGERIDO"
                )
                session.add(asignacion)

        # 5. Persistencia Documental (MongoDB)
        await mongo_db.final_records.insert_one({
            "radicado": radicado_id,
            "structured_data": final_data,
            "full_transcript": chat_history,
            "hash_seguridad": hash_seguridad,
            "metadata": {
                "session_id": session_id,
                "channel": "CALILEX_CHAT",
                "created_at": datetime.datetime.utcnow().isoformat()
            }
        })
        
        return {
            "status": "success",
            "radicado": radicado_id,
            "data": final_data,
            "message": "Conversación destilada, gobernada y radicada exitosamente bajo la Ley 1755."
        }
        
    except Exception as e:
        logger.error(f"Error al radicar desde chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Error en el cierre de la conversación")

from app.services.websocket_manager import ws_manager

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # ... resto del flujo de chat ...
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)
