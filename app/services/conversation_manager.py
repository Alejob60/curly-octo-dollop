import json
from typing import List, Dict, Optional, Tuple
from loguru import logger
import re
from app.core.config import settings
from app.core.db_clients import redis_client

class ConversationManager:
    """
    ST-14: Gestión de Contexto Unificada con Persistencia en Valkey L2.
    HU 1.1: Almacenamiento distribuido de historial de chat.
    """
    def __init__(self):
        self.redis = redis_client
        logger.info("🔌 Conversation Manager vinculado al Motor Global de Valkey.")

    async def get_history(self, session_id: str) -> List[Dict]:
        if not session_id: return []
        try:
            data = await self.redis.get(f"history:{session_id}")
            return json.loads(data) if data else []
        except Exception as e:
            logger.error(f"Error recuperando historial: {e}")
            return []

    async def save_history(self, session_id: str, history: List[Dict], ttl: int = 3600):
        if not session_id: return
        try:
            await self.redis.setex(f"history:{session_id}", ttl, json.dumps(history))
        except Exception as e:
            logger.error(f"Error guardando historial: {e}")

    async def distill_conversation(self, session_id: str) -> dict:
        """Extrae datos clave del historial para la radicación."""
        history = await self.get_history(session_id)
        chat_text = " ".join([m["content"] for m in history])
        
        cedula = re.search(r'\b\d{7,15}\b', chat_text)
        nombre = re.search(r'nombre es ([a-zA-Z\s]+)', chat_text, re.I)
        
        return {
            "citizen_name": nombre.group(1).strip() if nombre else "Ciudadano Anónimo",
            "citizen_id": cedula.group(0) if cedula else "Pendiente",
            "topic": "Petición / Queja Formal",
            "content": chat_text[:1000],
            "fuente_legal_base": "Ley 1755 de 2015",
            "suggested_dependency_id": "4173"
        }

conversation_manager = ConversationManager()
