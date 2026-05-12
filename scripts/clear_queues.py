import asyncio
from app.core.db_clients import mongo_manager

async def clear():
    db = mongo_manager.get_db()
    if db is None: return
    await db["pqrs_pending"].delete_many({})
    await db["pqrs_dlq"].delete_many({})
    print("Queues cleared.")

if __name__ == "__main__":
    asyncio.run(clear())
