import logging
from app.core.db_clients import redis_client

logger = logging.getLogger(__name__)

IDEM_PREFIX = "pqrs:idempotency:"

async def check_idempotency(key: str) -> bool:
    """Verifica si una solicitud ya fue procesada o está en curso."""
    if not key: return False
    exists = await redis_client.get(f"{IDEM_PREFIX}{key}")
    return exists is not None

async def mark_processed(key: str, ttl: int = 86400):
    """Marca una solicitud como 'en proceso' con un TTL de 24h por defecto."""
    if not key: return
    await redis_client.setex(f"{IDEM_PREFIX}{key}", ttl, "PROCESSING")
    logger.debug(f"🔒 [IDEMPOTENCY] Bloqueado: {key}")

async def unmark_processed(key: str):
    """Elimina el bloqueo si algo falla antes de encolar."""
    if not key: return
    await redis_client.delete(f"{IDEM_PREFIX}{key}")
