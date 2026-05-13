from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

def check_vertex_models():
    print(f"🔎 Iniciando auditoría de modelos en proyecto: {os.getenv('GCP_PROJECT_ID')}")
    try:
        # Inicializamos el cliente con el modo Vertex activado
        client = genai.Client(
            vertexai=True,
            project=os.getenv("GCP_PROJECT_ID"),
            location=os.getenv("GCP_LOCATION", "us-central1")
        )
        
        print("✅ Cliente Vertex inicializado. Listando modelos disponibles...")
        
        # Listamos los modelos filtrando por los de Google
        for model in client.models.list():
            if "gemini" in model.name.lower():
                print(f"📍 Modelo encontrado: {model.name} (ID: {model.compute_stats_common_metadata if hasattr(model, 'compute_stats_common_metadata') else 'N/A'})")
        
        # Prueba de fuego: una generación mínima
        print("\n🔥 Realizando prueba de generación...")
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents='ping'
        )
        print(f"✅ ÉXITO TOTAL. Respuesta: {response.text}")
        
    except Exception as e:
        print(f"❌ FALLO CRÍTICO: {e}")

if __name__ == "__main__":
    check_vertex_models()
