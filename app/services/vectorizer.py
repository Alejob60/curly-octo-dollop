from datetime import datetime, timezone

from loguru import logger

from app.core.azure_openai_client import get_text_embedding_async
from app.core.db_clients import mongo_db


class HistoricalVectorizerService:
    async def vectorize_document(self, document_id):
        document = await mongo_db.pqrsd_history.find_one({"_id": document_id})
        if not document:
            return False

        asunto = document.get("asunto") or ""
        if not asunto.strip():
            return False

        embedding = await get_text_embedding_async(asunto)
        if not embedding:
            return False

        await mongo_db.pqrsd_history.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "embedding": embedding,
                    "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        return True

    async def vectorize_pending(self, limit: int = 200):
        cursor = mongo_db.pqrsd_history.find(
            {
                "$or": [
                    {"embedding": {"$exists": False}},
                    {"embedding": []},
                    {"embedding": None},
                ]
            },
            projection={"_id": 1, "asunto": 1},
        ).limit(limit)

        updated = 0
        async for row in cursor:
            if await self.vectorize_document(row["_id"]):
                updated += 1

        logger.info(f"Vectorizacion historica completada: {updated} documentos actualizados.")
        return {
            "updated": updated,
            "scanned": limit,
        }


historical_vectorizer = HistoricalVectorizerService()
