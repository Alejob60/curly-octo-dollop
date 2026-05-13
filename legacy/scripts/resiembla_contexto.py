import asyncio
from loguru import logger
from app.services.legal_citation_engine import legal_citation_engine
from app.core.db_clients import mongo_manager
from app.core.config import settings

async def seed_legal_context():
    print("\n🌱 --- INICIANDO RESIEMBRA DE CONTEXTO JURÍDICO (MOTOR ASYNC V53.4) ---")
    
    db = mongo_manager.get_db()
    if not db:
        print("❌ CRÍTICO: No se pudo obtener la instancia de base de datos MongoDB.")
        return

    # 1. PRUEBA DE CONEXIÓN Y AUTENTICACIÓN
    try:
        await db.command("ping")
        print("✅ Autenticación exitosa en MongoDB Atlas.")
    except Exception as e:
        print(f"❌ FALLO DE AUTENTICACIÓN: {e}")
        print("👉 POR FAVOR VERIFICA: Usuario, Password y Whitelist de IP en el panel de Atlas.")
        return

    collection = db.normativa_colombia

    # 2. LIMPIEZA PREVIA
    print(f"🧹 Limpiando colección '{collection.name}' en DB '{db.name}'...")
    try:
        await collection.delete_many({})
        print("   [OK] Colección vaciada.")
    except Exception as e:
        print(f"❌ Fallo al vaciar colección: {e}")
        return

    # 3. DOCUMENTOS MAESTROS
    legal_corpus = [
        {
            "citacion_formato": "Ley 1755 de 2015",
            "articulo": "13",
            "texto_relevante": "Toda persona tiene derecho a presentar peticiones respetuosas a las autoridades por motivos de interés general o particular...",
            "ente_emisor": "Congreso de la República",
            "vigencia": True,
            "tags": ["general", "derecho_peticion", "ley_1755_2015"]
        },
        {
            "citacion_formato": "Ley 1751 de 2015",
            "articulo": "2",
            "texto_relevante": "El derecho fundamental a la salud es autónomo e irrenunciable en lo individual y en lo colectivo...",
            "ente_emisor": "Congreso de la República",
            "vigencia": True,
            "tags": ["salud", "medico", "ley_1751_2015"]
        },
        {
            "citacion_formato": "Resolución 2674 de 2013",
            "articulo": "12",
            "texto_relevante": "El personal manipulador de alimentos debe recibir capacitación en educación sanitaria y buenas prácticas de manufactura...",
            "ente_emisor": "Ministerio de Salud",
            "vigencia": True,
            "tags": ["alimentos", "sanitario", "capacitacion", "resolucion_2674_2013"]
        },
        {
            "citacion_formato": "Ley 489 de 1998",
            "articulo": "111",
            "texto_relevante": "Las Juntas de Acción Comunal son organizaciones cívicas, sociales y comunitarias de gestión autónoma...",
            "ente_emisor": "Congreso de la República",
            "vigencia": True,
            "tags": ["jac", "comunal", "junta", "ley_489_1998"]
        },
        {
            "citacion_formato": "Ley 1098 de 2006",
            "articulo": "18",
            "texto_relevante": "Derecho a la integridad personal. Los niños, las niñas y los adolescentes tienen derecho a ser protegidos...",
            "ente_emisor": "Congreso de la República",
            "vigencia": True,
            "tags": ["niños", "infancia", "escolar", "ley_1098_2006"]
        }
    ]

    print(f"📡 Vectorizando e Insertando {len(legal_corpus)} documentos...")
    
    for doc in legal_corpus:
        try:
            # Generamos el vector usando el SDK moderno heredado de V53.2
            vector = await legal_citation_engine._generate_embedding(doc["texto_relevante"])
            doc["embedding"] = vector
            
            # Inserción asíncrona segura con Motor
            await collection.insert_one(doc)
            print(f"   [OK] Sembrado: {doc['citacion_formato']} (Art. {doc['articulo']})")
        except Exception as e:
            print(f"   [ERROR] Fallo al sembrar {doc['citacion_formato']}: {e}")

    print("\n✨ --- RESIEMBRA COMPLETADA CON ÉXITO ---")
    print("👉 RECUERDA ACTIVAR EL ÍNDICE VECTORIAL 'vector_index_normativa' EN EL PANEL DE ATLAS SEARCH.")

if __name__ == "__main__":
    asyncio.run(seed_legal_context())
