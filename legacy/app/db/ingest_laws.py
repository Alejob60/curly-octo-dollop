import asyncio
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from loguru import logger

# Permite ejecutar: python app/db/ingest_laws.py
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings
from app.core.azure_openai_client import get_text_embedding

# --- FLUJOS DE CASOS DE USO (SOP - Standard Operating Procedures) ---
WORKFLOW_DATA = [
    {
        "case_type": "Malla Vial / Huecos",
        "description": "Reporte de baches, huecos o deterioro de calles y avenidas.",
        "procedure": "1. Validar ubicación en sistema geográfico. 2. Remitir a Secretaría de Infraestructura. 3. Informar al ciudadano que el tiempo de inspección es de 10 días.",
        "template": "Se ha recibido su reporte de daño en la malla vial. Su solicitud fue remitida a la Secretaría de Infraestructura bajo el programa 'Obras de Corazón'..."
    },
    {
        "case_type": "Impuesto Predial / Catastro",
        "description": "Dudas sobre avalúos, recibos de pago o errores en el cobro del predial.",
        "procedure": "1. Verificar número de predio. 2. Consultar base de Hacienda. 3. Solicitar al ciudadano copia del último recibo si hay inconsistencias.",
        "template": "Respecto a su consulta sobre el predio {{PREDIO}}, le informamos que puede descargar su factura en el portal oficial o solicitar revisión de avalúo ante Catastro..."
    },
    {
        "case_type": "Salud / Urgencias / Sisbén",
        "description": "Solicitudes relacionadas con atención médica, asignación de citas o puntaje Sisbén.",
        "procedure": "1. Identificar nivel de urgencia. 2. Remitir a Secretaría de Salud o oficina Sisbén. 3. Priorizar como 'CRITICAL' si hay riesgo de vida.",
        "template": "Dada la naturaleza de su solicitud de salud, hemos escalado su caso con prioridad ALTA a la red de salud del distrito..."
    }
]

# (Mantenemos LAWS_DATA del paso anterior...)
LAWS_DATA = [
    {"law_name": "Ley 1755 de 2015", "article_number": 13, "content": "Derecho de petición fundamental..."},
    {"law_name": "Ley 1755 de 2015", "article_number": 14, "content": "Término de 15 días para responder..."},
    {"law_name": "CPACA", "article_number": 5, "content": "Derecho a trato digno ante autoridades..."}
]

def get_embedding(text: str):
    """Genera embedding usando Azure OpenAI."""
    try:
        return get_text_embedding(text)
    except Exception as e:
        logger.error(f"Error en embedding (Azure OpenAI): {str(e)}")
        raise RuntimeError("Azure OpenAI no configurado o deployment de embeddings no disponible.") from e

async def setup_indexes(db):
    """Crea índices vectoriales en ambas colecciones."""
    for coll_name in ["legal_knowledge", "workflow_templates"]:
        try:
            await db.command({
                "createIndexes": coll_name,
                "indexes": [{"name": "vector_index", "key": {"embedding": "cosmosSearch"},
                             "cosmosSearchOptions": {"kind": "vector-ivf", "numLists": 100, "similarity": "COS", "dimensions": settings.AZURE_OPENAI_EMBEDDING_DIMENSIONS}}]
            })
            logger.info(f"Índice creado en {coll_name}")
        except Exception: pass

async def ingest_all():
    logger.info("🚀 Iniciando Ingesta de Leyes y Casos de Uso...")

    # Generar embeddings ANTES de abrir la conexión Mongo
    # (evita que la conexión quede idle mientras se espera la API externa)
    logger.info("Generando embeddings...")
    laws_docs = []
    for law in LAWS_DATA:
        vector = get_embedding(law["content"])
        laws_docs.append({**law, "embedding": vector})

    workflow_docs = []
    for wf in WORKFLOW_DATA:
        vector = get_embedding(wf["description"])
        workflow_docs.append({**wf, "embedding": vector})

    # Inicializar cliente Mongo DESPUÉS de tener todos los datos listos
    logger.info("Conectando a MongoDB...")
    mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
    db = mongo_client[settings.MONGO_DB]
    laws_collection = db["legal_knowledge"]
    workflows_collection = db["workflow_templates"]

    await setup_indexes(db)

    await laws_collection.delete_many({})
    await laws_collection.insert_many(laws_docs)

    await workflows_collection.delete_many({})
    await workflows_collection.insert_many(workflow_docs)

    mongo_client.close()
    logger.success(f"✅ Ingesta Completa: {len(laws_docs)} Leyes y {len(workflow_docs)} Flujos de Trabajo.")

if __name__ == "__main__":
    asyncio.run(ingest_all())
