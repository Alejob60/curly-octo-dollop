from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from typing import List, Optional
from app.services.judicial_engine_service import judicial_engine
from loguru import logger
import json

router = APIRouter()

from app.services.conversation_manager import conversation_manager

@router.post("/process-multimodal")
async def process_multimodal_pqrsd(
    request: Request,
    issue: str = Form(...),
    session_id: Optional[str] = Form(None),
    files: List[UploadFile] = File(None)
):
    """
    ENDPOINT V25.5: Auditoría Multimodal con Manejo Nativo de Contexto.
    """
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")
    
    try:
        # 1. Recuperar Historial real
        history = []
        if session_id:
            history = await conversation_manager.get_history(session_id)
            
        logger.info(f"📥 Petición de {client_ip} (Sesión: {session_id}): {issue[:50]}...")
        
        import hashlib
        attached_files = []
        if files:
            for file in files:
                content = await file.read()
                file_hash = hashlib.sha256(content).hexdigest()
                attached_files.append({
                    "name": file.filename,
                    "mime_type": file.content_type,
                    "content": content,
                    "hash": file_hash,
                    "is_map_snapshot": any(x in file.filename.lower() for x in ["map", "georeferencia", "snapshot"])
                })
        
        # --- BYPASS DE IA PARA FORMULARIOS ESTRUCTURADOS (V32) ---
        if "BLOQUE" in issue.upper() and "COMPLETADO" in issue.upper():
            logger.info(f"⚡ Bypass de IA detectado: Procesando resumen estructurado...")
            result = await judicial_engine.run_multimodal_pqrsd_flow(
                issue=issue,
                history=history,
                attached_files=attached_files,
                client_ip=client_ip,
                user_agent=user_agent,
                session_id=session_id or "default"
            )
        else:
            # Flujo normal con IA para lenguaje natural
            result = await judicial_engine.run_multimodal_pqrsd_flow(
                issue=issue,
                history=history,
                attached_files=attached_files,
                client_ip=client_ip,
                user_agent=user_agent,
                session_id=session_id or "default"
            )
        
        # Validar que result no sea None antes de proceder
        if not result or result.get("status") == "error":
             logger.error("❌ Fallo en la generación del resultado del motor.")
             return result or {"status": "error", "respuesta_chat": "Error interno al procesar su solicitud."}

        # Guardar en Historial (V25.6: Siempre guardar user message para memoria)
        if session_id:
            history.append({"role": "user", "content": issue})
            if result.get("status") == "inquiry":
                history.append({
                    "role": "assistant", 
                    "content": f"```json\n{json.dumps(result)}\n```"
                })
            await conversation_manager.save_history(session_id, history)
            logger.debug(f"📜 Historial Guardado. Tamaño: {len(history)}")
            
        return result
        
    except Exception as e:
        logger.error(f"❌ Error en Gateway Multimodal V25.5: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/finalize-and-sign")
async def finalize_and_sign(
    request: Request,
    payload: dict
):
    """
    ENDPOINT V15 (ASÍNCRONO): Firma Electrónica y Generación vía Celery.
    """
    client_ip = request.client.host
    logger.info(f"🖋️ Solicitud de firma recibida desde {client_ip} (MODO ASÍNCRONO)")

    try:
        audit_data = payload.get("audit_draft")
        session_id = payload.get("session_id")

        if not audit_data:
             raise HTTPException(status_code=400, detail="Datos de auditoría faltantes")

        # 🚀 ENVIAR A COLA DE CELERY
        from app.tasks.pqrsd_tasks import task_finalize_and_sign_async

        # Enviamos la tarea al worker y retornamos el ID para seguimiento
        task = task_finalize_and_sign_async.delay(audit_data, client_ip, session_id)

        
        return {
            "status": "processing",
            "task_id": task.id,
            "message": "Su expediente está siendo sellado criptográficamente en el búnker de GCP. Por favor espere...",
            "logs_ejecucion": [
                "[SISTEMA] > Petición enviada al clúster de procesamiento.",
                "[WORKER] > Iniciando pipeline de inmutabilidad...",
                "[QUEUE] > Tarea registrada en Redis (Valkey)."
            ]
        }

    except Exception as e:
        logger.error(f"❌ Error al encolar firma: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

