from pymongo import MongoClient
from pymongo.server_api import ServerApi
import vertexai
from vertexai.language_models import TextEmbeddingModel
import os
from dotenv import load_dotenv

load_dotenv()

# Credenciales y Config GCP
GCP_PROJECT = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
password = "YCo9NuvlW1N6nVvj"
uri = f"mongodb+srv://adminRealculture:{password}@cluster0.ahzlqud.mongodb.net/?appName=Cluster0"
DB_NAME = "orbital_prime_atlas"

# Inicializar Vertex AI (GCP Native)
vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
model = TextEmbeddingModel.from_pretrained("text-embedding-004")

def get_embedding(text):
    embeddings = model.get_embeddings([text])
    return embeddings[0].values

LEGAL_DATA = [
    {
        "norma": "Ley Estatutaria 1751 de 2015",
        "cita": "Articulo 6: Principio de Continuidad",
        "text": "Las personas tienen derecho a recibir los servicios de salud de manera continua. La prohibición de interrupción del servicio por razones administrativas o económicas es absoluta.",
        "dependency_id": "4135"
    },
    {
        "norma": "Sentencia T-114/19",
        "cita": "Corte Constitucional de Colombia",
        "text": "El agotamiento del tope del SOAT no puede ser usado como barrera para la prestacion del servicio. La IPS debe continuar el tratamiento y la EPS debe asumir el excedente.",
        "dependency_id": "4135"
    },
    {
        "norma": "Ley 99 de 1993",
        "cita": "Gestion Ambiental",
        "text": "Otorga competencias al DAGMA para la proteccion del medio ambiente urbano y la gestion de riesgos por arboles o contaminacion.",
        "dependency_id": "4147"
    },
    {
        "norma": "Codigo Nacional de Transito (Ley 769/02)",
        "cita": "Normas de Movilidad",
        "text": "Regula la infraestructura vial y la seguridad de los ciudadanos en las vias publicas municipales.",
        "dependency_id": "4134"
    },
    {
        "norma": "Ley 1801 de 2016",
        "cita": "Codigo Nacional de Seguridad y Convivencia",
        "text": "Establece las normas para la sana convivencia, el control de ruido y el orden publico en el territorio nacional.",
        "dependency_id": "4137"
    }
]

def seed_legal_rag():
    print(f"🚀 Iniciando Seed VERTEX-NATIVE en {DB_NAME} (GCP Project: {GCP_PROJECT})...")
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        db = client[DB_NAME]
        collection = db["normativa_colombia"]

        collection.delete_many({})
        print("🗑️ Coleccion limpiada.")

        for doc in LEGAL_DATA:
            print(f"📦 Generando Vector Vertex AI para: {doc['norma']}...")
            doc["embedding"] = get_embedding(f"{doc['norma']} {doc['cita']} {doc['text']}")
            collection.insert_one(doc)

        print("\n✅ MONGO ATLAS POBLADO CON VERTEX AI.")
    except Exception as e:
        print(f"❌ Error en Seed: {e}")

if __name__ == "__main__":
    seed_legal_rag()
