import asyncio
import json
from app.core.db_clients import mongo_manager

async def check():
    db = mongo_manager.get_db()
    if db is None: return
    # List all collections
    cols = await db.list_collection_names()
    print(f"Collections: {cols}")
    
    for col in ["pqrs_pending", "pqrs_dlq"]:
        docs = await db[col].find().to_list(10)
        print(f"--- {col} ({len(docs)}) ---")
        for d in docs:
            d["_id"] = str(d["_id"])
            print(json.dumps({k: v for k, v in d.items() if k != 'embedding'}, indent=2))

if __name__ == "__main__":
    asyncio.run(check())
