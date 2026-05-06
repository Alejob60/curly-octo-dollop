import asyncio
import httpx
import json
from loguru import logger

async def run_govtech_demo():
    BASE_URL = "http://localhost:8000/api/v1"
    
    logger.info("🎬 INICIANDO DEMO DE CUMPLIMIENTO GOVTECH PR-01...")
    
    # 1. Simular Ingestión Omnicanal (WhatsApp)
    logger.info("📱 PASO 1: Ingestión desde WhatsApp...")
    omni_payload = {
        "source": "whatsapp",
        "sender_id": "3157778899",
        "message": "Hola, soy ALEJANDRO GARZON CC 112233. Solicito la nulidad del comparendo D76001000 por falta de notificacion."
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        res = await client.post(f"{BASE_URL}/integrations/omnichannel/ingest", json=omni_payload)
        session_id = res.json()["session_id"]
        logger.success(f"✅ Caso recibido via WhatsApp. Session: {session_id}")

        # 2. Registrar Consentimiento (Ley 1581)
        logger.info("⚖️ PASO 2: Registro de Consentimiento Legal...")
        await client.post(f"{BASE_URL}/pqrs/register-consent", json={
            "session_id": session_id,
            "consent_type": "LEY_1581_GENERAL"
        })

        # 3. Finalizar y Sincronizar con Orfeo
        logger.info("🖋️ PASO 3: Generación Documental y Sincronización Orfeo...")
        res_final = await client.post(f"{BASE_URL}/pqrs/finalize", json={"session_id": session_id})
        
        if res_final.status_code == 200:
            data = res_final.json()
            if data.get("status") == "warning":
                logger.warning(f"⚠️ [AVISO] {data['message']}")
                logger.info(f"🆔 Radicado Orbital: {data['radicado_id']}")
                logger.info(f"⚖️ Acción: {data['action']}")
            else:
                logger.success(f"🏁 PROCESO COMPLETADO")
                logger.info(f"🆔 Radicado Orbital: {data['radicado_id']}")
                logger.info(f"🔗 Radicado Orfeo: {data['orfeo_id']}")
                logger.info(f"⏱️ Vencimiento Legal: {data['vencimiento_legal']}")
                logger.info(f"📄 Documentos: {len(data['artifacts'])}")
        else:
            logger.error(f"❌ Fallo en finalización: {res_final.text}")

if __name__ == "__main__":
    asyncio.run(run_govtech_demo())
