import asyncio
import os
import sys
import json
import time

# Path setup
sys.path.append(os.getcwd())

from app.services.judicial_engine_service import judicial_engine
from app.services.metrics_service import metrics_service
from loguru import logger

async def run_deterministic_probe():
    logger.info("🧪 INICIANDO PROBETA DE VALIDACIÓN FINAL (DÍA 5)")
    
    test_case = {
        "issue": "Mi placa ODR78G es un gemelo, me llegó fotomulta injusta. Soy Alejandro Garzon CC 83101005901.",
        "expected_case": "Impugnación por Placa Clonada (Gemelo)"
    }
    
    iterations = 5 # Para brevedad del test en CLI, pero extensible a 10
    results = []
    
    logger.info(f"🚀 Ejecutando {iterations} iteraciones para validar determinismo...")
    
    start_time = time.time()
    
    for i in range(iterations):
        logger.info(f"Iteración {i+1}/{iterations}...")
        res = await judicial_engine.run_multimodal_pqrsd_flow(
            issue=test_case["issue"],
            history=[],
            attached_files=[],
            session_id=f"qa-probe-{i}"
        )
        # Extraer datos clave para comparar consistencia
        summary = {
            "asunto": res["data_consolidada"]["hechos"]["asunto"],
            "cc": res["data_consolidada"]["peticionario"]["documento"],
            "status": res["status"]
        }
        results.append(json.dumps(summary, sort_keys=True))
    
    end_time = time.time()
    
    # --- ANÁLISIS DE RESULTADOS ---
    is_deterministic = len(set(results)) == 1
    avg_latency = (end_time - start_time) / iterations
    
    print("\n" + "="*50)
    print("📊 REPORTE DE CALIDAD DETERMINÍSTICA V36")
    print("="*50)
    print(f"✅ Determinismo de Extracción: {'100%' if is_deterministic else 'FALLO'}")
    print(f"⏱️ Latencia Promedio: {avg_latency:.2f}s")
    print(f"🎯 Caso Detectado: {json.loads(results[0])['asunto']}")
    print("="*50)
    
    health = await metrics_service.get_system_health()
    print(f"🏥 Salud del Sistema (MongoDB Metrics): {json.dumps(health, indent=2)}")
    
    if is_deterministic:
        logger.info("✨ QA PASSED: El motor es determinístico y auditable.")
    else:
        logger.error("❌ QA FAILED: Se detectaron variaciones en el output.")

if __name__ == "__main__":
    asyncio.run(run_deterministic_probe())
