import asyncio
from app.services.judicial_engine_service import judicial_engine
from loguru import logger
import os

async def run_rc_demo():
    logger.info("🏁 EJECUTANDO DEMO: ORBITAL PRIME RELEASE CANDIDATE")
    
    # Datos de la Actuación de Fiscalización
    citizen_data = {
        "name": "Ente de Control / Fiscalización Ambiental",
        "id": "CONT-CALI-2026"
    }
    
    issue = "Solicitud de información sobre ejecución presupuestal de inversión ambiental vigencia 2024 y comportamiento de indicadores de calidad de aire hasta julio 2025."
    
    try:
        result = await judicial_engine.run_release_candidate_flow(
            citizen_data=citizen_data,
            issue=issue
        )
        
        if result:
            print("\n" + "█" * 70)
            print("🏆 EXPEDIENTE RELEASE CANDIDATE GENERADO - ORBITAL PRIME PRO")
            print("█" * 70)
            print(f"📊 RADICADO:   {result['radicado']}")
            print(f"📁 VAULT RAÍZ: {result['vault_root']}")
            print(f"📝 LOG PENSAMIENTO: {result['log']} (Cargado en 03_Logs_Auditoria)")
            print(f"📄 DOCUMENTO 1: {result['docs'][0]} (Cargado en 01_Peticion_Ciudadana)")
            print(f"📄 DOCUMENTO 2: {result['docs'][1]} (Cargado en 02_Proyeccion_Dependencia)")
            print("-" * 70)
            print("VERIFICACIÓN: El sistema ha identificado Requerimiento de Ente de Control.")
            print("ACCIÓN: Se fijó término de 10 días y se emitió Auto de Requerimiento Interno.")
            print("█" * 70)
            
    except Exception as e:
        logger.error(f"Fallo en demo RC: {e}")

if __name__ == "__main__":
    asyncio.run(run_rc_demo())
