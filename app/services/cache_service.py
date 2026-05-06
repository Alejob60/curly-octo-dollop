import json
import hashlib
from loguru import logger
import redis.asyncio as redis
from app.core.config import settings

from app.core.db_clients import redis_client

class CacheService:
    def __init__(self):
        self.redis = redis_client
        logger.info("🚀 Cache de Respuesta vinculada al Motor Global de Valkey.")

    def _generate_key(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    async def get_response(self, key_text: str) -> dict:
        key = self._generate_key(key_text)
        try:
            data = await self.redis.get(f"ai_cache:{key}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Error lectura cache: {e}")
            return None

    async def set_response(self, key_text: str, response_data: dict, ttl: int = 600):
        key = self._generate_key(key_text)
        try:
            await self.redis.setex(f"ai_cache:{key}", ttl, json.dumps(response_data))
        except Exception as e:
            logger.error(f"Error escritura cache: {e}")
            pass

cache_service = CacheService()
