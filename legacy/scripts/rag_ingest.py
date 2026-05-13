import asyncio
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import vertexai
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
import hashlib
import urllib.parse

# 1. Configuración Vertex AI
vertexai.init(project="misybot-ai-beta", location="us-central1")
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

# 2. Configuración MongoDB Atlas (Blindada)
user = "adminRealculture"
password = urllib.parse.quote_plus("Alejob6005901@/")
cluster = "cluster0.ahzlqud.mongodb.net"
db_name = "orbital_prime_atlas"

ATLAS_URI = f"mongodb+srv://{user}:{password}@{cluster}/{db_name}?retryWrites=true&w=majority"

# 3. Corpus Legal de Prueba (La "Biblia" de Orbital Prime)
LEGAL_KNOWLEDGE = [
    {
        "source": "Ley 1755 de 2015",
        "title": "Derecho de Petición",
        "content": "Toda persona tiene derecho a presentar peticiones respetuosas a las autoridades. Términos: Interés general: 15 días. Documentos: 10 días. Consultas: 30 días.",
        "tags": ["tiempos", "ley 1755"]
    },
    {
        "source": "Manual de Cali",
        "title": "Secretaría de Movilidad",
        "content": "Competencias: Tránsito, transporte, fotomultas, semaforización y regulación vial.",
        "tags": ["movilidad", "multas"]
    },
    {
        "source": "Manual de Cali",
        "title": "Secretaría de Infraestructura",
        "content": "Competencias: Mantenimiento vial, baches, huecos y obras civiles municipales.",
        "tags": ["huecos", "infraestructura"]
    }
]

async def get_embedding(text: str):
    inputs = [TextEmbeddingInput(text, "RETRIEVAL_DOCUMENT")]
    embeddings = embedding_model.get_embeddings(inputs)
    return embeddings[0].values

async def ingest_legal_brain():
    logger.info("🧠 Iniciando Ingestión RAG Directa a Atlas...")
    
    try:
        client = AsyncIOMotorClient(ATLAS_URI)
        db = client[db_name]
        collection = db["legal_knowledge"]

        # Limpiar
        await collection.delete_many({})

        documents = []
        for doc in LEGAL_KNOWLEDGE:
            vector = await get_embedding(doc["content"])
            documents.append({
                "doc_id": hashlib.md5(doc["content"].encode()).hexdigest(),
                **doc,
                "embedding": vector
            })

        if documents:
            await collection.insert_many(documents)
            logger.success(f"✅ ÉXITO: {len(documents)} leyes indexadas en MongoDB Atlas.")
            
    except Exception as e:
        logger.error(f"Fallo crítico en ingestión Atlas: {e}")

if __name__ == "__main__":
    asyncio.run(ingest_legal_brain())
