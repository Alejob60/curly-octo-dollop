import os
import sys
import logging
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from app.api.v1 import pqrs, ingesta, metrics_router
from app.core.config import settings

# --- 🛡️ PROTOCOLO DE EVENT LOOP (Windows Fix) ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="Orbital Prime GovDocs Engine", version="65.14")

# 1. Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Servir Archivos Estáticos del Vault
if not os.path.exists("vault_digital"):
    os.makedirs("vault_digital")
app.mount("/vault_digital", StaticFiles(directory="vault_digital"), name="vault_digital")

# 3. Registro de Routers
app.include_router(pqrs.router, prefix="/api/v1/pqrs", tags=["PQRS Direct Flow"])
app.include_router(ingesta.router, prefix="/api/v1/pqrs", tags=["PQRS Unified Ingestion"])
app.include_router(metrics_router.router)

@app.get("/api/v1/health")
async def health_check():
    """V65.1: Health Check Maestro"""
    try:
        from app.services.pqrs_manager import pqrs_manager
        profiles = [p.get("ID") for p in pqrs_manager.registry.get("CASE_PROFILES", [])]
        return {
            "status": "ready",
            "message": "Sistema Orbital Prime V65.14 en línea",
            "version": "65.14.0",
            "available_profiles": profiles
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}

@app.on_event("startup")
async def startup_event():
    # --- 🏛️ MÓDULO 3: PREPARACIÓN RAG ---
    try:
        from app.services.rag_context import rag_manager
        await rag_manager.ensure_indices()
    except Exception as e:
        logger.error(f"⚠️ Error inicializando RAG: {e}")

    # --- ⚙️ MÓDULO: PROCESADOR DE COLA BATCH (V65.13) ---
    try:
        from app.services.queue_processor import process_pending_queue_loop
        asyncio.create_task(process_pending_queue_loop())
        logger.info("⚙️ [V65.13] Worker de Cola Batch activado.")
    except Exception as e:
        logger.error(f"❌ Fallo al iniciar Worker de Cola: {e}")

    logger.info(f"⚡ [V65.14] Motor Orbital Prime en línea (Ojo de Dios activado)")

@app.get("/")
async def root():
    return {
        "message": "Orbital Prime V65.14 Diamond Refactored is running",
        "version": "65.14.0",
        "status": "Diamond Refactored Stable",
        "legal_framework": "Multi-Ley (Ley 1755 / Ley 1437)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
