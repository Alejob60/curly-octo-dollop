import asyncio
import httpx
import json
import uuid
from loguru import logger

BASE_URL = "http://localhost:8000/api/v1"

async def run_demo_flow():
    session_id = f"demo-{uuid.uuid4().hex[:6]}"
    logger.info(f"🚀 Iniciando Demo Copilot Flow - Sesión: {session_id}")

    async with httpx.AsyncClient(timeout=300.0) as client:
        # 0. Health Check
        logger.info("Step 0: Verificando salud del motor Copilot...")
        health = await client.get(f"{BASE_URL}/copilot-engine/health")
        logger.info(f"Health: {health.json()}")

        # 1. INGESTA (Simulación Ciudadano)
        logger.info("Step 1: Radicación Ciudadana...")
        analyze_res = await client.post(f"{BASE_URL}/pqrs/analyze", json={
            "session_id": session_id,
            "message": "Mi nombre es Alejandro Garzón y quiero reportar un hueco enorme en la Avenida 6ta que dañó mi llanta ayer."
        })
        logger.debug(f"Analyze Res: {analyze_res.json()}")

        # Llenar slots necesarios para avanzar
        await client.post(f"{BASE_URL}/pqrs/update-slot", json={
            "session_id": session_id,
            "slots": {
                "documento": "12345678",
                "nombres": "Alejandro",
                "apellidos": "Garzón",
                "email": "alejandro.garzon.demo@example.com",
                "celular": "3001234567",
                "direccion": "Avenida 6ta Norte",
                "autorizacion_datos": True
            }
        })

        # 2. FINALIZACIÓN (IA genera documentos y pone en PENDIENTE_MAESTRA)
        logger.info("Step 2: IA generando documentos...")
        finalize_res = await client.post(f"{BASE_URL}/pqrs/finalize", json={"session_id": session_id})
        f_data = finalize_res.json()
        
        if finalize_res.status_code != 200:
            logger.error(f"❌ Error en Step 2: {finalize_res.status_code} - {finalize_res.text}")
            return

        radicado_id = f_data.get("radicado_id")
        next_step = f_data.get("next_step") or f_data.get("action")
        logger.success(f"✅ Radicado Creado: {radicado_id} - Estado: {next_step}")

        # 3. VISTO BUENO MAESTRO (Dashboard Gobernación)
        logger.info(f"Step 3: Aprobación Maestro para {radicado_id}...")
        master_res = await client.post(f"{BASE_URL}/copilot-engine/master-approve/{radicado_id}", json={
            "official_id": "FUNC-CENTRAL-001",
            "comments": "Traslado aprobado. Proyección IA correcta."
        })
        
        if master_res.status_code != 200:
            logger.error(f"❌ Error en Step 3: {master_res.status_code} - {master_res.text}")
            return

        logger.success(f"✅ {master_res.json().get('message', 'Aprobación maestra exitosa')}")

        # 4. VISTO BUENO DEPENDENCIA (Dashboard Movilidad)
        logger.info(f"Step 4: Aprobación Final Dependencia para {radicado_id}...")
        dep_res = await client.post(f"{BASE_URL}/copilot-engine/dependency-approve/{radicado_id}", json={
            "official_id": "FUNC-MOVILIDAD-042",
            "comments": "Respuesta final avalada técnica y jurídicamente."
        })
        
        if dep_res.status_code != 200:
            logger.error(f"❌ Error en Step 4: {dep_res.status_code} - {dep_res.text}")
            return

        logger.success(f"✅ {dep_res.json().get('message', 'Aprobación de dependencia exitosa')}")
        logger.info(f"📧 Notificación: {dep_res.json().get('notification')}")

        logger.info("🏁 Demo completada exitosamente.")

if __name__ == "__main__":
    try:
        asyncio.run(run_demo_flow())
    except Exception as e:
        logger.error(f"❌ Fallo en el script de demo: {e}")
