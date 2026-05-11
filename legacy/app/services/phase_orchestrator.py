import asyncio
import json
import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from loguru import logger
from app.core.db_clients import redis_client

class Phase(str, Enum):
    F1_IDENTIDAD = "fase_1_identidad"
    F2_TRIAJE = "fase_2_triaje"
    F3_ANALISIS = "fase_3_analisis"
    F5_CONFIRMACION = "fase_5_confirmacion"
    F4_EVIDENCIA = "fase_4_evidencia"
    F6_FIRMA_CIERRE = "fase_6_firma_cierre"

class PhaseGuard:
    """
    🛡️ PhaseGuard V54.0: Blindaje Atómico con Bloqueos de Sesión.
    Asegura que el flujo de PQRSD sea estrictamente secuencial y libre de condiciones de carrera.
    """
    
    def __init__(self):
        self.state_prefix = "pqrs:state:"
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    async def get_current_phase(self, session_id: str) -> Phase:
        state = await redis_client.hget(f"{self.state_prefix}{session_id}", "current_phase")
        if not state: return Phase.F1_IDENTIDAD
        try: return Phase(state)
        except ValueError: return Phase.F1_IDENTIDAD

    async def transition(self, session_id: str, new_phase: Phase, data: dict = None):
        """Realiza una transición bloqueada y atómica (Anti-Race Condition)."""
        lock = self._get_lock(session_id)
        
        async with lock:
            current = await self.get_current_phase(session_id)
            
            # Definimos el orden estricto de las fases
            phase_order = [
                Phase.F1_IDENTIDAD, 
                Phase.F2_TRIAJE, 
                Phase.F3_ANALISIS, 
                Phase.F4_EVIDENCIA, 
                Phase.F5_CONFIRMACION, 
                Phase.F6_FIRMA_CIERRE
            ]
            
            curr_idx = phase_order.index(current)
            target_idx = phase_order.index(new_phase)
            
            if target_idx < curr_idx:
                logger.warning(f"🚫 [PHASEGUARD] Retroceso bloqueado: {current} -> {new_phase}")
                return False

            # Actualización en Valkey con persistencia de timestamp
            update = {
                "current_phase": new_phase.value,
                "last_phase_change": datetime.datetime.utcnow().isoformat()
            }
            
            if data:
                clean_data = {str(k): str(v) for k, v in data.items() if v is not None and k != "current_phase"}
                update.update(clean_data)
                
            await redis_client.hset(f"{self.state_prefix}{session_id}", mapping=update)
            logger.success(f"🔄 [PHASEGUARD] Transición Atómica Exitosa: {current} -> {new_phase} [Session: {session_id}]")
            return True

phase_guard = PhaseGuard()
