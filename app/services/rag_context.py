import os
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.db_clients import mongo_manager
from loguru import logger
import json

class RAGContextManager:
    """
    💎 MÓDULO 3: CONTEXT MONGODB & RAG (V65.5)
    Gestor de contexto legal asíncrono para inyección estructurada en prompts.
    """
    
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self.db = db or mongo_manager.get_db()
        self.collection_name = "legal_rag_store"
        self.token_limit = 8000 # Límite estricto de seguridad para el contexto
        
    async def ensure_indices(self):
        """Optimización de queries mediante índices (Requerimiento Módulo 3)"""
        if self.db is None: return
        try:
            await self.db[self.collection_name].create_index([("law_type", 1)])
            await self.db[self.collection_name].create_index([("tags", 1)])
            # Índice de texto para búsqueda básica si no hay vector search disponible
            await self.db[self.collection_name].create_index([("content", "text")])
            logger.info(f"✅ Índices de RAG verificados en {self.collection_name}")
        except Exception as e:
            logger.error(f"❌ Error creando índices RAG: {e}")

    async def get_legal_grounding(self, law_type: str, query_text: str = "", limit: int = 5) -> str:
        """
        Consulta MongoDB (Motor) para obtener artículos relevantes.
        Estructura el resultado como clave-valor para la IA.
        """
        if self.db is None:
            logger.warning("⚠️ MongoDB no disponible. Usando fallback de contexto vacío.")
            return "CONTEXTO_LEGAL_NO_DISPONIBLE"

        try:
            # Query optimizada
            filter_query = {"law_type": law_type}
            if query_text:
                # Búsqueda por texto si se provee
                filter_query["$text"] = {"$search": query_text}
            
            cursor = self.db[self.collection_name].find(filter_query).limit(limit)
            docs = await cursor.to_list(length=limit)
            
            if not docs:
                logger.info(f"ℹ️ No se encontró contexto específico para {law_type}")
                return "SIN_CONTEXTO_ESPECIFICO_DISPONIBLE"

            # Estructuración Estricta (Requerimiento Módulo 3)
            context_blocks = []
            current_tokens = 0
            
            for doc in docs:
                source = doc.get("title") or doc.get("law_type", "NORMA_VIGENTE")
                block = f"[FUENTE: {source}]\n"
                block += f"CONTENIDO: {doc.get('content', '')}\n"
                block += f"RELEVANCIA: {doc.get('summary', '')}\n---\n"
                
                # Estimación ruda de tokens (1 token ~ 4 caracteres)
                estimated_tokens = len(block) // 4
                if current_tokens + estimated_tokens > self.token_limit:
                    logger.warning("⚠️ Límite de tokens RAG alcanzado. Truncando contexto.")
                    break
                
                context_blocks.append(block)
                current_tokens += estimated_tokens

            return "\n".join(context_blocks)

        except Exception as e:
            logger.error(f"🔥 Error en RAG Context: {e}")
            return "ERROR_RECUPERANDO_CONTEXTO_LEGAL"

rag_manager = RAGContextManager()
