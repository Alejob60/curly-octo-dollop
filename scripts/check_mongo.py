import asyncio
import json
from app.core.db_clients import mongo_manager

async def check():
    db = mongo_manager.get_db()
    if db is None:
        print("MongoDB is None")
        return
    docs = await db["pqrs_pending"].find().to_list(100)
    for d in docs:
        d["_id"] = str(d["_id"])
        print(json.dumps(d, indent=2))

if __name__ == "__main__":
    asyncio.run(check())
