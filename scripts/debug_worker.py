import asyncio
import os
from loguru import logger
from app.core.db_clients import mongo_manager
from app.services.queue_processor import _worker_task

async def debug():
    logger.info("🕵️ Debugging Worker Task...")
    db = mongo_manager.get_db()
    if db is None:
        logger.error("MongoDB not available")
        return
        
    doc = await db["pqrs_pending"].find_one({"status": "PROCESSING"})
    if not doc:
        logger.warning("No PROCESSING task found. Checking PENDING...")
        doc = await db["pqrs_pending"].find_one({"status": "PENDING"})
        
    if doc:
        logger.info(f"Found task: {doc['idempotency_key']}")
        await _worker_task(doc)
    else:
        logger.error("No task found to process.")

if __name__ == "__main__":
    asyncio.run(debug())
