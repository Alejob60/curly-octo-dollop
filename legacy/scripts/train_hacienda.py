import asyncio
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient
import vertexai
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
import hashlib
import urllib.parse

# 1. Configuración Vertex AI
vertexai.init(project="misybot-ai-beta", location="us-central1")
embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")

# 2. Configuración MongoDB Atlas
user = "adminRealculture"
password = urllib.parse.quote_plus("Alejob6005901@/")
cluster = "cluster0.ahzlqud.mongodb.net"
db_name = "orbital_prime_atlas"
ATLAS_URI = f"mongodb+srv://{user}:{password}@{cluster}/{db_name}?retryWrites=true&w=majority"

# 3. Conocimiento de Hacienda Municipal (Cali Oficial)
CONOCIMIENTO_HACIENDA = [
    {
        "source": "Acuerdo 0434 de 2017",
        "title": "Estatuto Tributario Municipal",
        "content": "Establece la obligación de la administración de expedir certificados de paz y salvo tributario previa verificación de los pagos de Predial e ICA. El término para certificaciones es de 10 días hábiles.",
        "tags": ["hacienda", "paz y salvo", "impuestos"]
    },
    {
        "source": "Ley 1995 de 2019",
        "title": "Límites al Impuesto Predial",
        "content": "Establece que el incremento del impuesto predial unificado no podrá exceder del IPC más ocho puntos porcentuales, salvo en casos de mutación física o cambio de uso del suelo.",
        "tags": ["predial", "limites", "cobro excesivo"]
    }
]

async def get_embedding(text: str):
    inputs = [TextEmbeddingInput(text, "RETRIEVAL_DOCUMENT")]
    embeddings = embedding_model.get_embeddings(inputs)
    return embeddings[0].values

async def train_hacienda_brain():
    logger.info("🧠 Entrenando Cerebro de Hacienda en Atlas...")
    try:
        client = AsyncIOMotorClient(ATLAS_URI)
        db = client[db_name]
        col = db["legal_knowledge"]
        
        for item in CONOCIMIENTO_HACIENDA:
            vector = await get_embedding(item["content"])
            await col.insert_one({
                "doc_id": hashlib.md5(item["content"].encode()).hexdigest(),
                **item,
                "embedding": vector
            })
        logger.success(f"✅ Conocimiento de Hacienda inyectado en la memoria vectorial.")
    except Exception as e:
        logger.error(f"Fallo en entrenamiento Hacienda: {e}")

if __name__ == "__main__":
    asyncio.run(train_hacienda_brain())
