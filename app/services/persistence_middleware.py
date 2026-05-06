import json
import hashlib
import datetime
import asyncio
from typing import Dict, Any, Optional
from loguru import logger

from app.core.db_clients import mongo_db, postgres_manager
from app.models.sql_models import FlowTelemetry

class PersistenceMiddleware:
    """
    V63.1: Middleware de Persistencia Resiliente.
    Garantiza sincronización en tiempo real y NO bloquea el flujo principal ante fallos.
    Incluye sistema de reintentos en background para PostgreSQL.
    """
    
    def __init__(self):
        self.mongo = mongo_db
        self.pg_factory = postgres_manager.get_session
    
    async def save_flow_step(self, session_id: str, step_data: dict) -> Optional[str]:
        """Guarda telemetría: MongoDB (siempre) + PostgreSQL (fallback seguro)"""
        try:
            timestamp = datetime.datetime.utcnow()
            
            # Preparar registro
            record = {
                "session_id": session_id,
                "step_name": step_data.get("step", "unknown"),
                "timestamp": timestamp,
                "context_snapshot": step_data.get("context", {}),
                "user_actions": step_data.get("user_input", {}),
                "ai_responses": step_data.get("ai_output", {}),
                "documents_generated": step_data.get("documents", []),
                "processing_time": step_data.get("processing_time", 0.0)
            }
            
            # Generar hash de integridad
            hash_base = json.dumps({k: v for k, v in record.items() if k != "timestamp"}, sort_keys=True, default=str)
            integrity_hash = hashlib.sha256(hash_base.encode()).hexdigest()
            record["integrity_hash"] = integrity_hash
            
            # 1. MongoDB (rápido, tolerante)
            try:
                if self.mongo is not None:
                    await self.mongo["flow_telemetry"].insert_one({**record})
                    logger.debug(f"📊 [TELEMETRY] MongoDB: {session_id}/{record['step_name']}")
            except Exception as e:
                logger.warning(f"⚠️ [TELEMETRY] MongoDB falló: {e}")
            
            # 2. PostgreSQL (NO bloqueante)
            try:
                async with self.pg_factory() as pg_session:
                    telemetry = FlowTelemetry(
                        session_id=record["session_id"],
                        step_name=record["step_name"],
                        timestamp=timestamp,
                        context_snapshot=record["context_snapshot"],
                        integrity_hash=integrity_hash,
                        processing_time=record["processing_time"]
                    )
                    pg_session.add(telemetry)
                    await pg_session.commit()
                    logger.debug(f"📊 [TELEMETRY] PostgreSQL: {session_id}/{record['step_name']}")
            except Exception as pg_err:
                # 🔥 NO romper el flujo: solo loguear y reintentar
                logger.warning(f"⚠️ [TELEMETRY] PostgreSQL fallback (no crítico): {pg_err}")
                asyncio.create_task(self._retry_pg_save(record, timestamp, integrity_hash))
            
            return integrity_hash
            
        except Exception as e:
            logger.error(f"❌ [TELEMETRY] Error general: {e}")
            return None
    
    async def _retry_pg_save(self, record: dict, timestamp: datetime.datetime, integrity_hash: str, max_retries: int = 2):
        """Reintento en background para PostgreSQL"""
        for attempt in range(max_retries):
            try:
                await asyncio.sleep(2 ** attempt)
                async with self.pg_factory() as pg_session:
                    telemetry = FlowTelemetry(
                        session_id=record["session_id"],
                        step_name=record["step_name"],
                        timestamp=timestamp,
                        context_snapshot=record["context_snapshot"],
                        integrity_hash=integrity_hash,
                        processing_time=record["processing_time"]
                    )
                    pg_session.add(telemetry)
                    await pg_session.commit()
                    logger.info(f"✅ [TELEMETRY] Reintento PostgreSQL exitoso para {record['session_id']}")
                    return
            except:
                pass

    async def get_session_context(self, session_id: str) -> dict:
        """Recupera el último contexto válido para reanudar flujo"""
        try:
            if self.mongo is None: return {}
            last_record = await self.mongo["flow_telemetry"].find_one(
                {"session_id": session_id},
                sort=[("timestamp", -1)]
            )
            return last_record["context_snapshot"] if last_record else {}
        except:
            return {}

persistence_middleware = PersistenceMiddleware()
