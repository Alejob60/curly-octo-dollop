import redis
import json
from app.core.config import settings
from loguru import logger

class SessionManager:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def update_draft(self, session_id: str, data: dict):
        """Actualiza el borrador de la PQRSD en Redis."""
        current = self.get_draft(session_id)
        current.update(data)
        
        # Evaluar si está lista para despacho
        if current.get("citizen_name") and current.get("citizen_id") and current.get("content"):
            current["is_ready"] = True
            
        self.redis.set(f"draft:{session_id}", json.dumps(current), ex=3600) # Expira en 1h
        return current

    def get_draft(self, session_id: str) -> dict:
        """Obtiene el borrador actual."""
        data = self.redis.get(f"draft:{session_id}")
        return json.loads(data) if data else {}

    def clear_session(self, session_id: str):
        self.redis.delete(f"draft:{session_id}")

session_manager = SessionManager()
