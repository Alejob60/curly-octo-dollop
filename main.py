import os
import sys
import logging
import asyncio

# --- 🛡️ PROTOCOLO DE EVENT LOOP (Windows Fix) ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- 🛡️ PROTOCOLO DE SILENCIO ABSOLUTO (V1.1) ---
# Redirigimos la salida estándar inmediatamente para capturar ruidos de importación de los SDKs de Google
try:
    _devnull = open(os.devnull, 'w')
    _old_stdout = sys.stdout
    sys.stdout = _devnull
    
    # Configurar niveles de log antes de importar
    logging.getLogger('google').setLevel(logging.ERROR)
    logging.getLogger('absl').setLevel(logging.ERROR)

    from fastapi import FastAPI, Request, Depends, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    import datetime
    from app.api.v1 import (        ingesta, dashboard, citizen, public, dispatch, auth, 
        judicial, ingest, master_data, tasks, chat, learning, 
        staff, multimodal, governance, pqrs, integrations, governance_copilot,
        verify, telemetry
    )
    from app.api.v1.dashboard import copilot as copilot_dashboard
    from loguru import logger
    from app.core.config import settings
    from app.core.auth import get_current_user
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    
finally:
    # Restauramos la salida para que Loguru pueda imprimir sus mensajes de salud oficiales
    sys.stdout = _old_stdout
    _devnull.close()

# 1. Instanciar la Aplicación y el Limitador
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Orbital Prime GovDocs Engine", version="50.9")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Servir Archivos Estáticos del Vault
if not os.path.exists("vault_digital"):
    os.makedirs("vault_digital")
app.mount("/vault_digital", StaticFiles(directory="vault_digital"), name="vault_digital")

# 2. Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Registro de Routers
app.include_router(public.router, prefix=settings.API_V1_STR + "/public", tags=["Public"])
app.include_router(auth.router, prefix=settings.API_V1_STR + "/auth", tags=["Authentication"])
app.include_router(ingesta.router, prefix=settings.API_V1_STR + "/ingesta", tags=["Ingestion Engine"])
app.include_router(multimodal.router, prefix=settings.API_V1_STR + "/multimodal", tags=["Multimodal AI"])
app.include_router(dashboard.router, prefix=settings.API_V1_STR + "/dashboard", tags=["Governance Dashboard"])
app.include_router(copilot_dashboard.router, prefix=settings.API_V1_STR + "/dashboard/copilot", tags=["Copilot"])
app.include_router(governance.router, prefix=settings.API_V1_STR + "/governance", tags=["Governance Operations"])
app.include_router(citizen.router, prefix=settings.API_V1_STR + "/citizen", tags=["Citizen Portal"])
app.include_router(dispatch.router, prefix=settings.API_V1_STR + "/dispatch", tags=["Dispatch Engine"])
app.include_router(judicial.router, prefix=settings.API_V1_STR + "/judicial", tags=["Judicial Engine"])
app.include_router(master_data.router, prefix=settings.API_V1_STR + "/master-data", tags=["Master Data"])
app.include_router(tasks.router, prefix=settings.API_V1_STR + "/tasks", tags=["Asynchronous Tasks"])
app.include_router(chat.router, prefix=settings.API_V1_STR + "/chat", tags=["AI Chat"])
app.include_router(learning.router, prefix=settings.API_V1_STR + "/learning", tags=["Continuous Learning"])
app.include_router(staff.router, prefix=settings.API_V1_STR + "/staff", tags=["Staff Management"])
app.include_router(pqrs.router, prefix=settings.API_V1_STR + "/pqrs", tags=["PQRS Direct Flow"])
app.include_router(telemetry.router, prefix=settings.API_V1_STR + "/telemetry", tags=["Telemetría (Repair Plan V62.9)"])
app.include_router(governance_copilot.router, prefix=settings.API_V1_STR + "/copilot-engine", tags=["Governance Copilot"])
app.include_router(integrations.router, prefix=settings.API_V1_STR, tags=["Interoperabilidad PR-01"])
app.include_router(verify.router, prefix="", tags=["Public Verification"])

from app.core.db_clients import valkey_manager

@app.on_event("startup")
async def startup_event():
    logger.info("⚡ Iniciando verificaciones de salud de infraestructura...")
    await valkey_manager.check_connection()

@app.get("/ping")
async def ping():
    return {"status": "alive", "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/metrics")
async def get_metrics():
    """
    SPRINT 4: Exposición de KPIs para Monitoreo Gubernamental.
    """
    from app.services.compliance_monitor import compliance_monitor
    return await compliance_monitor.get_metrics()

@app.get("/")
async def root():
    return {
        "message": "Orbital Prime GovDocs Engine is running",
        "version": "60.0.1",
        "status": "Diamond Ready",
        "legal_framework": "Ley 1755 / Ley 1581"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
