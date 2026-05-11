import asyncio
import os
import json
import hashlib
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.vertex_client import vertex_client
from loguru import logger

class LegalRAGPipeline:
    """
    💎 MÓDULO 6: PIPELINE RAG (V65.9)
    Ingesta continua, chunking inteligente y vectorización de leyes.
    """
    
    def __init__(self):
        self.client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = self.client[settings.MONGO_DB]
        self.collection = self.db["legal_rag_store"]
        self.chunk_size = 1500 # Caracteres por chunk
        self.chunk_overlap = 200

    def _create_chunks(self, text: str) -> List[str]:
        """Chunking simple con solapamiento para mantener contexto"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += self.chunk_size - self.chunk_overlap
        return chunks

    async def ingest_law(self, law_id: str, title: str, content: str, tags: List[str] = None):
        """
        Procesa una ley completa: limpia, divide, vectoriza y persiste.
        """
        logger.info(f"📥 [RAG_PIPELINE] Iniciando ingesta: {title} ({law_id})")
        
        chunks = self._create_chunks(content)
        logger.info(f"✂️ Generados {len(chunks)} chunks para {law_id}")

        for i, chunk_text in enumerate(chunks):
            # 1. Generar ID único para el chunk (Evitar duplicados)
            chunk_hash = hashlib.sha256(f"{law_id}_{i}_{chunk_text[:50]}".encode()).hexdigest()
            
            # 2. Generar Embedding (IA Real)
            embedding = await vertex_client.generate_embedding(chunk_text)
            
            # 3. Preparar Documento
            doc = {
                "chunk_id": chunk_hash,
                "law_type": law_id.upper(),
                "title": title,
                "content": chunk_text,
                "article_id": f"Art {i+1} (Auto-Chunk)",
                "summary": chunk_text[:200] + "...",
                "tags": tags or [],
                "embedding": embedding, # Para Vector Search
                "metadata": {
                    "source": "manual_ingestion",
                    "version": "2026.1"
                }
            }
            
            # 4. Upsert en MongoDB
            await self.collection.update_one(
                {"chunk_id": chunk_hash},
                {"$set": doc},
                upsert=True
            )
            
        logger.success(f"✅ [RAG_PIPELINE] Ingesta completada para {law_id}. Total: {len(chunks)} documentos.")

async def run_sample_ingestion():
    pipeline = LegalRAGPipeline()
    
    # Ejemplo: Ley 1755 de 2015
    ley_1755_text = """
    Artículo 13. Objeto y modalidades del derecho de petición ante autoridades. 
    Toda persona tiene derecho a presentar peticiones respetuosas a las autoridades, 
    en los términos señalados en este código, por motivos de interés general o particular, 
    y a obtener pronta resolución completa y de fondo sobre la misma.
    """
    
    await pipeline.ingest_law(
        law_id="LEY_1755",
        title="Ley 1755 de 2015 - Derecho de Petición",
        content=ley_1755_text,
        tags=["peticion", "derechos", "transparencia"]
    )

if __name__ == "__main__":
    asyncio.run(run_sample_ingestion())
