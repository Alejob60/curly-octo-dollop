import vertexai
from vertexai.generative_models import GenerativeModel
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

vertexai.init(project=PROJECT_ID, location=LOCATION)

def list_models():
    print(f"🔎 Verificando modelos en {PROJECT_ID} ({LOCATION})...")
    try:
        # Nota: La SDK de Vertex no tiene un list_models directo tan sencillo como AI Studio,
        # pero podemos intentar inicializar un modelo base.
        model = GenerativeModel("gemini-1.5-flash")
        print(f"✅ Modelo 'gemini-1.5-flash' inicializado.")
        
        model_001 = GenerativeModel("gemini-1.5-flash-001")
        print(f"✅ Modelo 'gemini-1.5-flash-001' inicializado.")

        model_002 = GenerativeModel("gemini-1.5-flash-002")
        print(f"✅ Modelo 'gemini-1.5-flash-002' inicializado.")
        
    except Exception as e:
        print(f"❌ Error al verificar modelos: {e}")

if __name__ == "__main__":
    list_models()
