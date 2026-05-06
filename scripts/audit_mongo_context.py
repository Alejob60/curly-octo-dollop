import asyncio
import json
from loguru import logger
from app.core.db_clients import mongo_db

async def audit_mongo():
    print("\n🔍 --- AUDITORÍA DE CONTEXTO JURÍDICO (MONGODB ATLAS) ---")
    
    try:
        # 1. Conteo Total
        total_docs = await mongo_db.normativa_colombia.count_documents({})
        print(f"📊 TOTAL DOCUMENTOS EN COLECCIÓN: {total_docs}")

        if total_docs == 0:
            print("❌ LA BASE DE DATOS ESTÁ VACÍA. No hay leyes sembradas.")
            return

        # 2. Análisis de Estructura de un Documento Muestra
        sample = await mongo_db.normativa_colombia.find_one()
        print(f"📄 DOCUMENTO MUESTRA ENCONTRADO:")
        print(f"   - Norma: {sample.get('citacion_formato', sample.get('norma'))}")
        print(f"   - Artículo: {sample.get('articulo')}")
        print(f"   - Tiene Vector (Embedding): {'SÍ' if 'embedding' in sample else 'NO'}")
        if 'embedding' in sample:
            print(f"   - Dimensiones del Vector: {len(sample['embedding'])}")
        
        # 3. Verificación de Leyes Críticas
        print("\n📜 VERIFICACIÓN DE LEYES CLAVE:")
        leyes_a_buscar = ["Ley 1755 de 2015", "Ley 1843 de 2017", "Ley 769 de 2002"]
        for ley in leyes_a_buscar:
            found = await mongo_db.normativa_colombia.find_one({"citacion_formato": {"$regex": ley, "$options": "i"}})
            status = "✅ SEMBRADA" if found else "❌ FALTANTE"
            print(f"   - {ley}: {status}")

    except Exception as e:
        print(f"🔥 ERROR AL CONSULTAR MONGO: {e}")

if __name__ == "__main__":
    asyncio.run(audit_mongo())
