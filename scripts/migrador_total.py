import os
import asyncio
from pymongo import MongoClient
import urllib.parse
from loguru import logger

# 1. Configuración de Conexiones
# ORIGEN (VM GCP) - Usamos la URI exacta del .env con blindaje
SOURCE_USER = "adminRealculture"
SOURCE_PASS = urllib.parse.quote_plus("Alejob6005901@/")
SOURCE_IP = "34.134.235.169"
SOURCE_DB = "govdocs_db"
SOURCE_URI = f"mongodb://{SOURCE_USER}:{SOURCE_PASS}@{SOURCE_IP}:27017/{SOURCE_DB}?authSource=admin&directConnection=true"

# DESTINO (Atlas)
ATLAS_USER = "adminRealculture"
ATLAS_PASS = urllib.parse.quote_plus("Alejob6005901@/")
ATLAS_CLUSTER = "cluster0.ahzlqud.mongodb.net"
ATLAS_DB = "orbital_prime_atlas"
ATLAS_URI = f"mongodb+srv://{ATLAS_USER}:{ATLAS_PASS}@{ATLAS_CLUSTER}/{ATLAS_DB}?retryWrites=true&w=majority"

async def migrar_todo():
    logger.info("🚚 Iniciando Migración Total: VM -> MongoDB Atlas")
    
    try:
        # Conectar a Origen
        src_client = MongoClient(SOURCE_URI, serverSelectionTimeoutMS=5000)
        # Verificar conexión
        src_client.admin.command('ping')
        logger.success("✅ Conectado exitosamente a la VM local.")
        
        src_db = src_client[SOURCE_DB]
        collections = src_db.list_collection_names()
        
        # Conectar a Destino
        dest_client = MongoClient(ATLAS_URI)
        dest_db = dest_client[ATLAS_DB]
        
        logger.info(f"Colecciones detectadas para migrar: {collections}")

        for col_name in collections:
            if col_name.startswith("system."): continue
            
            logger.info(f"📦 Migrando colección: {col_name}...")
            
            docs = list(src_db[col_name].find())
            if not docs:
                logger.warning(f"La colección {col_name} está vacía.")
                continue

            # Insertar en bloques para mayor rendimiento
            # Limpiamos los IDs para evitar duplicados si se corre de nuevo
            for d in docs: d.pop("_id", None)
            
            dest_db[col_name].insert_many(docs)
            logger.success(f"   Done: {len(docs)} documentos movidos a Atlas.")

        logger.success("🏁 MIGRACIÓN COMPLETADA. Toda la data de la VM está ahora en Atlas.")

    except Exception as e:
        logger.error(f"❌ Fallo crítico en la migración: {e}")
        logger.info("TIP: Asegúrate de que tu IP actual esté en la 'Whitelist' de la VM de GCP.")

if __name__ == "__main__":
    asyncio.run(migrar_todo())
