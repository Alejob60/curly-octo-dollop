import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

# Intentar obtener la URL de diferentes variables
MONGODB_URL = os.getenv("MONGODB_URI") or os.getenv("MONGODB_CONNECTION_STRING") or "mongodb://localhost:27017"
DB_NAME = "orbital_prime_atlas"
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

client_genai = genai.Client(api_key=GOOGLE_API_KEY)

async def get_embedding(text):
    response = client_genai.models.embed_content(
        model="text-embedding-004",
        contents=text,
        config=genai.types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
    )
    return response.embeddings[0].values

LEGAL_DATA = [
    {
        "norma": "Ley Estatutaria 1751 de 2015",
        "cita": "Articulo 6: Principio de Continuidad",
        "text": "Las personas tienen derecho a recibir los servicios de salud de manera continua. La prohibición de interrupción del servicio por razones administrativas o económicas es absoluta."
    },
    {
        "norma": "Sentencia T-114/19",
        "cita": "Corte Constitucional de Colombia",
        "text": "El agotamiento del tope del SOAT no puede ser usado como barrera para la prestacion del servicio. La IPS debe continuar el tratamiento y la EPS debe asumir el excedente para posterior recobro al ADRES."
    },
    {
        "norma": "Decreto 780 de 2016",
        "cita": "Regulacion Unica del Sector Salud",
        "text": "Define las competencias de las Secretarias de Salud Municipales para la inspeccion, vigilancia y control de la red prestadora de servicios de salud."
    },
    {
        "norma": "Ley 99 de 1993",
        "cita": "Fundamentos de la Politica Ambiental",
        "text": "Otorga competencias al DAGMA para la gestion del medio ambiente y la flora urbana, incluyendo la tala y trasplante de arboles en riesgo."
    }
]

async def seed_legal_rag():
    print(f"🚀 Iniciando Seed en {DB_NAME}...")
    print(f"🔗 URL (masked): {MONGODB_URL[:20]}...")
    
    try:
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DB_NAME]
        collection = db["normativa_colombia"]

        # Verificar conexion
        await client.admin.command('ping')
        print("✅ Conexion exitosa a MongoDB Atlas.")

        # Limpiar coleccion previa
        await collection.delete_many({})

        for doc in LEGAL_DATA:
            print(f"📦 Indexando: {doc['norma']}...")
            doc["embedding"] = await get_embedding(f"{doc['norma']} {doc['cita']} {doc['text']}")
            await collection.insert_one(doc)

        print("✅ Seed Legal completado.")
    except Exception as e:
        print(f"❌ Error en Seed: {e}")

if __name__ == "__main__":
    asyncio.run(seed_legal_rag())
