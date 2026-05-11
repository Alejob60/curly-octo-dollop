import asyncio
import json
import datetime
import time
from typing import Dict, Any, Optional, AsyncGenerator
from loguru import logger
from fastapi import BackgroundTasks
from app.core.db_clients import redis_client
from app.services.phase_orchestrator import phase_guard, Phase

from app.services.confidence_auditor import confidence_auditor

class MasterOrchestrator:
    """
    💎 MÓDULO 5: ORQUESTADOR & ASYNC (V65.12)
    Gestor de concurrencia, semáforos, streaming de eventos (SSE) y blindaje de IA.
    """
    
    def __init__(self):
        # Semáforo para limitar procesamiento de IA concurrente
        self.ai_semaphore = asyncio.Semaphore(5)
        self.state_prefix = "pqrs:state:"
        self.progress_prefix = "progress:"

    async def emit_event(self, session_id: str, phase: Phase, message: str, progress: int, data: dict = None):
        """
        Persiste el estado en Redis para que el frontend lo consuma vía polling o SSE.
        🛡️ [PROTECTION V65.11] No sobreescribir si ya está completo.
        """
        progress_key = f"{self.progress_prefix}{session_id}"
        
        # Verificar estado actual
        current = await redis_client.get(progress_key)
        if current and '"status": "complete"' in current:
            logger.info(f"⏭️ [EVENT_SKIP] Sesión {session_id} ya completada. Ignorando evento: {message}")
            return

        event_payload = {
            "session_id": session_id,
            "phase": phase.value,
            "message": message,
            "progress": progress,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "data": data or {}
        }
        
        # Persistencia atómica en Redis
        await redis_client.setex(progress_key, 600, json.dumps(event_payload))
        
        # Log estructurado
        logger.info(f"📡 [EVENT_EMIT] {json.dumps(event_payload)}")

    async def execute_task_with_semaphore(self, task_func, *args, **kwargs):
        """Ejecuta una tarea de IA bajo el control del semáforo"""
        async with self.ai_semaphore:
            return await task_func(*args, **kwargs)

    async def run_shielded_analysis(self, session_id: str, original_prompt: str, ai_logic_func):
        """
        💎 MÓDULO 4: PIPELINE SEGURO (V65.12)
        Llamada IA -> Auditoría Confianza -> Retry con Backoff
        """
        import os
        max_retries = int(os.getenv("MAX_AI_RETRIES", 2))
        
        last_ai_data = {}
        last_audit = {"score": 0.0, "passed": False}

        for attempt in range(max_retries + 1):
            try:
                # 1. Llamada a la IA (esto ya tiene retries internos en vertex_client)
                ai_data = await self.execute_task_with_semaphore(ai_logic_func)
                
                # 2. Auditoría de Confianza
                audit = await confidence_auditor.evaluate(original_prompt, ai_data)
                
                if audit["passed"]:
                    return ai_data, audit
                
                last_ai_data = ai_data
                last_audit = audit
                
                logger.warning(f"⚠️ [LOW_CONFIDENCE] Intento {attempt+1} fallido (Score: {audit['score']:.2f}).")
                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.info(f"🔄 Reintentando en {wait}s...")
                    await asyncio.sleep(wait)
            except Exception as e:
                logger.error(f"❌ Error en intento {attempt+1} del pipeline: {e}")
                if attempt == max_retries: raise e
                
        return last_ai_data, last_audit

    async def sse_event_generator(self, session_id: str) -> AsyncGenerator[str, None]:
        """
        Generador para Server-Sent Events (SSE). 
        Permite al frontend recibir actualizaciones en tiempo real.
        """
        last_progress = -1
        while True:
            progress_raw = await redis_client.get(f"{self.progress_prefix}{session_id}")
            if progress_raw:
                data = json.loads(progress_raw)
                curr_progress = data.get("progress", 0)
                
                if curr_progress != last_progress:
                    yield f"data: {json.dumps(data)}\n\n"
                    last_progress = curr_progress
                
                if data.get("status") == "complete" or curr_progress >= 100:
                    break
            
            await asyncio.sleep(1) # Polling interno ligero para el stream SSE

orchestrator = MasterOrchestrator()
