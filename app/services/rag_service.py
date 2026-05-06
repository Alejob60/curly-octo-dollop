import os
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from loguru import logger
import vertexai
from vertexai.language_models import TextEmbeddingModel

class RAGService:
    def __init__(self):
        # Usar la URI que funcionó en el test
        self.uri = settings.MONGODB_CONNECTION_URL
        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client["orbital_prime_atlas"]
        self.legal_collection = self.db["normativa_colombia"]
        self.history_collection = self.db["pqrs_historico"]
        
        # Inicializar Vertex AI (GCP Native)
        try:
            vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
            self.model = TextEmbeddingModel.from_pretrained("text-embedding-004")
            logger.info(f"🚀 Vertex AI RAG inicializado en proyecto: {settings.GCP_PROJECT_ID}")
        except Exception as e:
            logger.error(f"Fallo al inicializar Vertex AI: {e}")
            self.model = None

    async def _get_embedding(self, text: str) -> List[float]:
        """Genera vector de embedding usando Vertex AI (Créditos GCP)."""
        if not self.model: return []
        try:
            embeddings = self.model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            logger.warning(f"Vertex Embedding fallido: {e}")
            return []

    async def search_legal_normative(self, query: str, limit: int = 3) -> List[Dict]:
        """Búsqueda híbrida usando Vertex AI."""
        vector = await self._get_embedding(query)
        results = []

        if vector:
            try:
                pipeline = [{"$vectorSearch": {"index": "vector_index_legal", "path": "embedding", "queryVector": vector, "numCandidates": 100, "limit": limit}}]
                async for doc in self.legal_collection.aggregate(pipeline):
                    results.append(doc)
            except Exception as e:
                logger.debug(f"Atlas Vector Search no disponible, usando fallback: {e}")

        if not results:
            async for doc in self.legal_collection.find({"$or": [{"norma": {"$regex": query, "$options": "i"}}, {"text": {"$regex": query, "$options": "i"}}]}).limit(limit):
                results.append(doc)
        
        return results

    async def get_combined_context(self, query: str) -> str:
        try:
            legal = await self.search_legal_normative(query)
            if not legal: 
                return "No se encontró contexto legal específico. Aplica la normativa general para el sector."
            parts = ["--- CONTEXTO LEGAL RECUPERADO (Vertex-GCP Grounding) ---"]
            for item in legal:
                parts.append(f"NORMA: {item.get('norma')}\nCITA: {item.get('cita')}\nCONTENIDO: {item.get('text')}\n")
            return "\n".join(parts)
        except Exception as e:
            logger.warning(f"RAG fallido (Error DB): {e}. Usando contexto general.")
            return "No se encontró contexto legal específico debido a un problema técnico. Aplica la normativa general para el sector (ej: Ley 1751 para salud, Ley 99 para ambiente, Ley 769 para tránsito)."

rag_service = RAGService()
