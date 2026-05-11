import asyncio
from scripts.rag_ingest import get_embedding
from motor.motor_asyncio import AsyncIOMotorClient
import urllib.parse
from loguru import logger

async def main():
    user = "adminRealculture"
    password = urllib.parse.quote_plus("Alejob6005901@/")
    uri = f"mongodb+srv://{user}:{password}@cluster0.ahzlqud.mongodb.net/orbital_prime_atlas"
    
    client = AsyncIOMotorClient(uri)
    db = client["orbital_prime_atlas"]
    col = db["legal_precedents"]
    
    logger.info("🧠 Vectorizando precedentes legales en Atlas...")
    docs = await col.find({"embedding": {"$exists": False}}).to_list(length=100)
    
    count = 0
    for d in docs:
        text = d.get("content") or d.get("hechos") or d.get("resumen")
        if text:
            vector = await get_embedding(text)
            await col.update_one({"_id": d["_id"]}, {"$set": {"embedding": vector}})
            count += 1
    
    logger.success(f"✅ Se han vectorizado {count} precedentes legales en Atlas.")

if __name__ == "__main__":
    asyncio.run(main())
