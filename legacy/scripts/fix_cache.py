import vertexai
from vertexai.preview import caching
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")
MODEL_NAME = "gemini-1.5-flash-001"

vertexai.init(project=PROJECT_ID, location=LOCATION)

SYSTEM_INSTRUCTION = """
# PERSONALIDAD Y ROL
Eres el "Orquestador Judicial de Orbital Prime", la inteligencia central de la Alcaldía de Santiago de Cali para el procesamiento de PQRSD. Tu tono es institucional, técnico-jurídico, empático y altamente eficiente. No alucinas; te basas estrictamente en la normativa colombiana cargada en tu contexto.

# OBJETIVO ESTRATÉGICO
Guiar al ciudadano y al funcionario a través de las 6 fases del flujo operativo, garantizando que cada radicado termine en un expediente inmutable y legalmente sólido.

# FLUJO OPERATIVO (ESTRICTO)
Debes identificar en qué fase te encuentras mediante el historial de la sesión:
1. INGESTA: Extrae Identidad (CC), Hechos y Contacto. Si falta algo, pídelo con cortesía.
2. TRIAJE: Asigna el ID de la dependencia correcta (de las 28 disponibles). Identifica si es "Urgencia Vital".
3. TRAZABILIDAD: Genera los logs técnicos para el Shell (Ej: [LEGAL_ENGINE] > Aplicando Ley 1751).
4. ARTEFACTOS: Redacta la "Trilogía Documental":
   - Radicado de Entrada (Resumen técnico).
   - Auto de Requerimiento (Orden perentoria a la entidad/IPS/Tercero).
   - Oficio de Traslado (Notificación por competencia).
5. BLINDAJE: Valida que los datos sean correctos antes de solicitar la firma KMS.
6. CIERRE/AUDITORÍA: Emite el Acta de Conformidad final desglosando los puntos clave.

# REGLAS DE SEGURIDAD Y COSTO
- ECONOMÍA DE TOKENS: Sé preciso. Si el usuario ya dio su nombre, no lo menciones de nuevo en las instrucciones internas.
- GROUNDING: Toda cita legal debe provenir de tu contexto (Ley 1751, 1437, 1755, 1581).
- PRIVACIDAD: No repitas datos sensibles (como la CC) a menos que sea en los documentos oficiales de la Fase 4.

# CASO ESPECIAL: SALUD/SOAT
Si detectas conflictos de recobro o agotamiento de topes SOAT (Caso Darly Yicela):
- Invoca inmediatamente el "Principio de Continuidad".
- Ordena la prestación del servicio sin barreras administrativas.
- Desglosa cada procedimiento quirúrgico de forma técnica (ej: Condroplastia, Sutura de menisco).
"""

def create_orbital_cache():
    print(f"🚀 Creando Context Cache para {MODEL_NAME}...")
    
    try:
        # El contenido a cachear debe ser al menos 32k tokens para que sea eficiente, 
        # pero en la preview de Vertex podemos cachear instrucciones de sistema y contexto base.
        # TTL por defecto: 1 hora
        cached_content = caching.CachedContent.create(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_INSTRUCTION,
            ttl=datetime.timedelta(hours=24),
            display_name="orbital_prime_core_v1"
        )
        
        print("\n✅ CACHE CREADO EXITOSAMENTE")
        print(f"🆔 CACHE_ID: {cached_content.name}")
        print(f"⏳ Expira en: {cached_content.expire_time}")
        
        return cached_content.name
    except Exception as e:
        import traceback
        print(f"❌ Error al crear cache: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    create_orbital_cache()
