from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse
import asyncio, logging, json
from typing import AsyncGenerator, Dict

logger = logging.getLogger(__name__)

class SSEManager:
    """
    💎 [V65.14] Gestor de Notificaciones en Tiempo Real (SSE).
    Mantiene canales abiertos por session_id o tracking_id.
    """
    def __init__(self):
        self.clients: Dict[str, asyncio.Queue] = {}

    async def emit_status(self, tracking_id: str, event: dict):
        """Envía un evento al cliente conectado."""
        if tracking_id in self.clients:
            try:
                await self.clients[tracking_id].put(f"data: {json.dumps(event)}\n\n")
            except Exception as e:
                logger.error(f"❌ Fallo al emitir SSE para {tracking_id}: {e}")

    async def event_generator(self, request: Request, tracking_id: str) -> AsyncGenerator[str, None]:
        """Generador asíncrono para el streaming SSE."""
        queue = asyncio.Queue()
        self.clients[tracking_id] = queue
        logger.info(f"🔌 [SSE] Cliente conectado: {tracking_id}")
        
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    # Esperar evento con heartbeat para mantener conexión viva
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield event
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            self.clients.pop(tracking_id, None)
            logger.info(f"🔌 [SSE] Cliente desconectado: {tracking_id}")

sse_manager = SSEManager()
