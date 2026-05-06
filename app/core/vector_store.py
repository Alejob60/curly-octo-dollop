import math

from sqlalchemy import text

from app.core.db_clients import AsyncSessionLocal, mongo_db
from loguru import logger
from app.core.azure_openai_client import get_text_embedding

class VectorStore:
    def __init__(self):
        pass

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right:
            return -1.0
        size = min(len(left), len(right))
        if size == 0:
            return -1.0

        left_values = left[:size]
        right_values = right[:size]
        numerator = sum(a * b for a, b in zip(left_values, right_values))
        left_norm = math.sqrt(sum(a * a for a in left_values))
        right_norm = math.sqrt(sum(b * b for b in right_values))
        if left_norm == 0 or right_norm == 0:
            return -1.0
        return numerator / (left_norm * right_norm)

    def get_embedding(self, text_to_embed: str):
        """Genera embedding usando Azure OpenAI."""
        try:
            return get_text_embedding(text_to_embed)
        except Exception as e:
            logger.error(f"Error generando embedding: {str(e)}")
            return None

    async def upsert_legal_precedent(self, case_type: str, outcome: str, argument: str):
        """Guarda un fallo histórico en Postgres si hay pgvector; si no, lo persiste en Mongo."""
        embedding = self.get_embedding(argument)
        if not embedding:
            return

        precedent_document = {
            "case_type": case_type,
            "decision_outcome": outcome,
            "legal_argument": argument,
            "embedding": embedding,
        }

        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    query = text("""
                        INSERT INTO legal_precedents (case_type, decision_outcome, legal_argument, embedding)
                        VALUES (:ctype, :out, :arg, CAST(:emb AS vector))
                    """)
                    await session.execute(query, {
                        "ctype": case_type,
                        "out": outcome,
                        "arg": argument,
                        "emb": str(embedding)
                    })
                    logger.info(f"Precedente guardado en Postgres: {case_type}")
                    return
        except Exception as exc:
            logger.warning(f"No fue posible guardar precedente en Postgres, usando Mongo: {exc}")

        await mongo_db.legal_precedents.update_one(
            {
                "case_type": case_type,
                "decision_outcome": outcome,
                "legal_argument": argument,
            },
            {"$set": precedent_document},
            upsert=True,
        )
        logger.info(f"Precedente guardado en Mongo: {case_type}")

    async def search_similar_cases(self, query_text: str, limit: int = 3):
        """Busca precedentes por pgvector y cae a Mongo si Postgres no soporta esa ruta."""
        embedding = self.get_embedding(query_text)
        if not embedding:
            return []

        try:
            async with AsyncSessionLocal() as session:
                query = text("""
                    SELECT case_type, decision_outcome, legal_argument 
                    FROM legal_precedents 
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT :limit
                """)
                result = await session.execute(query, {"embedding": str(embedding), "limit": limit})
                cases = result.fetchall()
                if cases:
                    return [
                        {
                            "type": row[0],
                            "outcome": row[1],
                            "argument": row[2]
                        } for row in cases
                    ]
        except Exception as exc:
            logger.warning(f"Busqueda en Postgres no disponible; usando Mongo para precedentes: {exc}")

        documents = await mongo_db.legal_precedents.find({}, {"_id": 0}).to_list(length=200)
        ranked_cases = []
        for document in documents:
            precedent_embedding = document.get("embedding") or []
            similarity = self._cosine_similarity(embedding, precedent_embedding)
            ranked_cases.append(
                {
                    "type": document.get("case_type") or document.get("topic") or "PRECEDENTE",
                    "outcome": document.get("decision_outcome") or document.get("outcome") or document.get("legal_base") or "N/A",
                    "argument": document.get("legal_argument") or document.get("winning_argument") or document.get("topic") or "",
                    "similarity": similarity,
                }
            )

        ranked_cases.sort(key=lambda item: item.get("similarity", -1.0), reverse=True)
        return [
            {
                "type": item["type"],
                "outcome": item["outcome"],
                "argument": item["argument"],
            }
            for item in ranked_cases[:limit]
        ]

vector_store = VectorStore()
