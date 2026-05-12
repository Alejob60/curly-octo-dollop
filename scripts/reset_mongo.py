import asyncio
from app.core.db_clients import mongo_manager

async def reset():
    db = mongo_manager.get_db()
    if db is None: return
    res = await db["pqrs_pending"].update_many(
        {"status": "PROCESSING"}, 
        {"$set": {"status": "PENDING"}}
    )
    print(f"Reset {res.modified_count} tasks.")

if __name__ == "__main__":
    asyncio.run(reset())
