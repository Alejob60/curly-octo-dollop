import asyncio
import os
import shutil
from loguru import logger
from app.core.db_clients import redis_client, postgres_manager
from sqlalchemy import text

async def system_wipe():
    print("\n🧹 --- INICIANDO PURGA FORENSE DEL SISTEMA ---")
    
    # 1. LIMPIEZA DE BÓVEDA (FILESYSTEM)
    vault_path = "vault_digital"
    print(f"📁 Limpiando Bóveda Digital: {vault_path}...")
    if os.path.exists(vault_path):
        for item in os.listdir(vault_path):
            item_path = os.path.join(vault_path, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    print(f"   [OK] Carpeta eliminada: {item}")
                elif os.path.isfile(item_path) and item != ".gitkeep":
                    os.remove(item_path)
                    print(f"   [OK] Archivo eliminado: {item}")
            except Exception as e:
                print(f"   [ERROR] No se pudo eliminar {item}: {e}")

    # 2. LIMPIEZA DE POSTGRESQL (AUDIT & PROFILES)
    print("🐘 Limpiando Base de Datos PostgreSQL...")
    async with postgres_manager.get_session() as session:
        try:
            # Desactivamos triggers temporalmente para truncar rápido
            await session.execute(text("TRUNCATE TABLE audit_ledger RESTART IDENTITY CASCADE;"))
            await session.execute(text("TRUNCATE TABLE citizen_profiles RESTART IDENTITY CASCADE;"))
            await session.commit()
            print("   [OK] Tablas truncadas: audit_ledger, citizen_profiles")
        except Exception as e:
            print(f"   [ERROR] Fallo al limpiar PostgreSQL: {e}")

    # 3. LIMPIEZA DE REDIS (VALKEY)
    print("🔌 Limpiando Motor de Sesiones Redis/Valkey...")
    try:
        await redis_client.flushdb()
        print("   [OK] Base de datos Redis vaciada (FLUSHDB)")
    except Exception as e:
        print(f"   [ERROR] Fallo al limpiar Redis: {e}")

    print("\n✨ --- SISTEMA 100% LIMPIO Y LISTO PARA ENTREGA ---")

if __name__ == "__main__":
    asyncio.run(system_wipe())
