import json
from typing import List, Dict, Any
from fastapi import WebSocket
from loguru import logger

class WebSocketManager:
    """
    ST-23: Gestor de Conexiones WebSocket para Sincronización en Tiempo Real.
    Maneja el broadcast de actualizaciones de fase y eventos de gobernanza.
    """
    def __init__(self):
        # Mapeo de session_id -> Lista de websockets activos
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.debug(f"🔌 WebSocket conectado para sesión: {session_id}")

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.debug(f"🔌 WebSocket desconectado para sesión: {session_id}")

    async def broadcast_phase_update(self, session_id: str, phase_name: str, data: dict):
        """
        Emite un evento de cambio de fase al frontend para re-renderizado reactivo.
        """
        if session_id in self.active_connections:
            message = {
                "type": "PHASE_UPDATED",
                "phase": phase_name,
                "data_consolidada": data
            }
            payload = json.dumps(message)
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.error(f"Error emitiendo update de fase: {e}")

    async def broadcast_governance(self, event: dict):
        """Broadcast general para el dashboard de gobernanza."""
        payload = json.dumps(event)
        # Por ahora emitimos a todas las sesiones activas (o una sesión de admin dedicada)
        for sessions in self.active_connections.values():
            for connection in sessions:
                try:
                    await connection.send_text(payload)
                except:
                    pass

ws_manager = WebSocketManager()
