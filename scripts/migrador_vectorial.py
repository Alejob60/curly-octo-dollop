import os
import asyncio
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger
import vertexai
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
import hashlib

# 1. Configuración de Credenciales (Extraídas de Variables de Entorno)
LOCAL_MONGO_URI = os.getenv("LOCAL_MONGO_URI", "mongodb://localhost:27017")
ATLAS_MONGO_URI = os.getenv("MONGO_ATLAS_URI")
PROJECT_ID = os.getenv("VERTEX_AI_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

if not ATLAS_MONGO_URI:
    logger.error("❌ Falta la variable MONGO_ATLAS_URI")
    exit(1)

# 2. Inicialización de Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

async def get_embedding(text: str) -> list:
    """Llamada a Vertex AI para generar el vector (768 dimensiones)."""
    try:
        inputs = [TextEmbeddingInput(text, "RETRIEVAL_DOCUMENT")]
        embeddings = embedding_model.get_embeddings(inputs)
        return embeddings[0].values
    except Exception as e:
        logger.warning(f"Error generando embedding: {e}")
        return []

async def migrar_y_vectorizar():
    logger.info("🚀 Iniciando Migración Vectorial a MongoDB Atlas...")
    
    # Conexiones
    local_client = MongoClient(LOCAL_MONGO_URI)
    local_db = local_client["govdocs_db"]
    
    atlas_client = AsyncIOMotorClient(ATLAS_MONGO_URI)
    atlas_db = atlas_client["orbital_prime_atlas"]

    colecciones = ["manuales_leyes", "pqrs_historico"]

    for col_name in colecciones:
        logger.info(f"📦 Procesando colección: {col_name}")
        local_docs = list(local_db[col_name].find())
        
        if not local_docs:
            logger.warning(f"La colección {col_name} está vacía en local.")
            continue

        migrated_count = 0
        for doc in local_docs:
            # Limpiar _id original para evitar conflictos
            doc.pop("_id", None)
            
            # Si es un manual de ley, generar vector del contenido
            if "content" in doc or "texto" in doc:
                text_to_vector = doc.get("content") or doc.get("texto")
                if text_to_vector:
                    doc["embedding_vector"] = await get_embedding(text_to_vector)
                    doc["vector_status"] = "PROCESSED"
            
            # Insertar en Atlas
            await atlas_db[col_name].update_one(
                {"doc_id": doc.get("doc_id", hashlib.md5(str(doc).encode()).hexdigest())},
                {"$set": doc},
                upsert=True
            )
            migrated_count += 1
            if migrated_count % 10 == 0:
                logger.debug(f"Migrados {migrated_count} documentos de {col_name}")

        logger.success(f"✅ Migración de {col_name} completada: {migrated_count} docs.")

    logger.info("🎯 Proceso finalizado exitosamente.")

if __name__ == "__main__":
    asyncio.run(migrar_y_vectorizar())
