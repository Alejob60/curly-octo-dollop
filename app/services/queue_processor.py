import asyncio
import os
import time
import json
from datetime import datetime
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.services.pqrs_manager import pqrs_manager
from app.services.priority_calculator import calculate_priority_score
from app.services.sse_manager import sse_manager
from app.core.db_clients import mongo_manager, redis_client

# Configuración de Colecciones
COL_PENDING = "pqrs_pending"
COL_DLQ = "pqrs_dlq"
MAX_WORKERS = int(os.getenv("MAX_PQRS_WORKERS", "4"))
SEM = asyncio.Semaphore(MAX_WORKERS)

async def enqueue_pqrs(payload: dict, source: str, idem_key: str, priority_data: dict = None):
    """Inserta una solicitud en la cola priorizada de MongoDB."""
    try:
        db = mongo_manager.get_db()
        if db is None:
            logger.error("❌ MongoDB no disponible para encolar")
            return
            
        # Calcular prioridad si no viene
        if not priority_data:
            priority_data = calculate_priority_score(payload)
            
        doc = {
            "idempotency_key": idem_key,
            "source": source,
            "status": "PENDING",
            "payload": payload,
            "priority_score": priority_data["score"],
            "priority_level": priority_data["level"],
            "created_at": time.time(),
            "retries": 0,
            "max_retries": 3
        }
        await db[COL_PENDING].update_one(
            {"idempotency_key": idem_key},
            {"$setOnInsert": doc},
            upsert=True
        )
        logger.info(f"📥 [QUEUE] Encolado: {idem_key} | Prioridad: {priority_data['level']}")
    except Exception as e:
        logger.error(f"❌ Fallo al encolar PQRS: {e}")

async def process_pending_queue_loop():
    """
    💎 Worker continuo Priorizado para procesar la cola (46k legacy + nuevas).
    """
    logger.info("⚙️ [WORKER] Iniciando loop de cola priorizada...")
    db = mongo_manager.get_db()
    while db is None:
        await asyncio.sleep(2)
        db = mongo_manager.get_db()

    # Crear índices
    await db[COL_PENDING].create_index([("status", 1), ("priority_score", -1), ("created_at", 1)])
    await db[COL_PENDING].create_index([("idempotency_key", 1)], unique=True)
    
    logger.success(f"⚙️ [WORKER] Operativo. Concurrencia máx: {MAX_WORKERS}")

    while True:
        try:
            # Buscar siguiente tarea pendiente por PRIORIDAD (DESC)
            doc = await db[COL_PENDING].find_one_and_update(
                {"status": "PENDING"},
                {"$set": {"status": "PROCESSING", "started_at": time.time()}},
                sort=[("priority_score", -1), ("created_at", 1)]
            )
            
            if not doc:
                await asyncio.sleep(5)
                continue

            asyncio.create_task(_worker_task(doc))

        except Exception as e:
            logger.error(f"🔥 Error en loop de cola: {e}")
            await asyncio.sleep(10)

async def _worker_task(doc: dict):
    """Tarea individual del worker con streaming de eventos."""
    idem_key = doc["idempotency_key"]
    payload = doc["payload"]
    session_id = f"batch-{idem_key[:8]}"
    db = mongo_manager.get_db()

    async with SEM:
        try:
            logger.info(f"🚀 [TASK_START] {idem_key} | Nivel: {doc.get('priority_level')}")
            await sse_manager.emit_status(idem_key, {"status": "PROCESSING", "message": "Iniciando análisis judicial priorizado..."})
            
            # 1. Iniciar flujo Diamond (Extracción + Análisis IA + RAG)
            pqrs_manager.extract_basic_info(session_id, payload.get("descripcion", ""))
            
            await sse_manager.emit_status(idem_key, {"status": "ANALYZING", "message": "Generando borrador técnico fundamentado..."})
            await pqrs_manager.background_process_full_analysis(session_id, payload.get("descripcion", ""))
            
            # 2. Inyectar datos de contacto (Simulación)
            state_key = f"pqrs:state:{session_id}"
            await redis_client.hset(state_key, mapping={
                "email": payload.get("email") or "notificaciones@cali.gov.co",
                "celular": payload.get("celular") or "3000000000",
                "confirmado": "True",
                "autorizacion_datos": "True"
            })
            
            # 3. Finalizar y generar PDFs (Diamond V65.14 con Guardian activo)
            await sse_manager.emit_status(idem_key, {"status": "GENERATING", "message": "Certificando integridad y generando PDFs..."})
            result = await pqrs_manager.finalize_pqrs(session_id)
            
            # 4. Actualizar Éxito
            await db[COL_PENDING].update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "status": "COMPLETED", 
                    "finished_at": time.time(),
                    "radicado": result.get("radicado_id"),
                    "documents": result.get("documents")
                }}
            )
            
            await sse_manager.emit_status(idem_key, {
                "status": "COMPLETED", 
                "radicado": result.get("radicado_id"),
                "urls": [d["url"] for d in result.get("documents", [])]
            })
            
            logger.success(f"✅ [TASK_SUCCESS] {idem_key} -> {result.get('radicado_id')}")

        except Exception as e:
            logger.error(f"❌ [TASK_FAIL] {idem_key}: {e}")
            retries = doc.get("retries", 0) + 1
            
            # Emitir fallo a SSE
            await sse_manager.emit_status(idem_key, {"status": "FAILED", "error": str(e)})
            
            if retries >= doc.get("max_retries", 3):
                await db[COL_PENDING].delete_one({"_id": doc["_id"]})
                await db[COL_DLQ].insert_one({
                    **doc, "status": "FAILED", "error": str(e), "failed_at": time.time()
                })
            else:
                await db[COL_PENDING].update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"status": "PENDING", "retries": retries, "last_error": str(e)}}
                )
