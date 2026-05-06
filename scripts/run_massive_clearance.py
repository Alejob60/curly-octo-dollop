import asyncio
from app.services.batch_processing_service import batch_processor
from app.core.db_clients import AsyncSessionLocal
from app.models.sql_models import RadicadoLegacy
from sqlalchemy import select
from loguru import logger

async def run_massive_demo():
    print("\n" + "🏁" * 30)
    print("DEMO FINAL: OPERACIÓN DESCONGESTIÓN 47,000")
    print("🏁" * 30 + "\n")

    # 1. Identificar el cluster más grande (Hacienda/Catastro o Movilidad)
    async with AsyncSessionLocal() as session:
        query = select(RadicadoLegacy.cluster_id).filter(RadicadoLegacy.cluster_id != None).limit(1)
        res = await session.execute(query)
        cluster_id = res.scalar()

    if not cluster_id:
        logger.error("No hay clusters para procesar. Corre primero la clusterización.")
        return

    # 2. Datos del Secretario que Firma en Bloque
    official_data = {
        "id": "SEC-CALI-01",
        "name": "Secretaría General de Cali",
        "title": "Oficina de Descongestión Institucional",
        "legal_base": "En virtud del Plan de Choque 2026, se procede a dar respuesta de fondo a los radicados represados del último trimestre 2025, garantizando el derecho fundamental de petición (Ley 1755)."
    }

    # 3. Ejecutar la Firma Masiva
    processed = await batch_processor.process_cluster_in_batch(cluster_id, official_data)

    print("\n" + "🏆" * 40)
    print("RESULTADO DE LA MISIÓN")
    print("🏆" * 40)
    print(f"✅ CLUSTER PROCESADO: {cluster_id}")
    print(f"✅ CASOS EVACUADOS:   {processed}")
    print(f"📁 ARCHIVOS EN VAULT: Se han creado {processed} expedientes individuales.")
    print(f"🔐 SEGURIDAD:         Firma SHA-256 aplicada a cada radicado.")
    print("🏆" * 40)
    print("Cali ha sido liberada del cuello de botella institucional.")

if __name__ == "__main__":
    asyncio.run(run_massive_demo())
