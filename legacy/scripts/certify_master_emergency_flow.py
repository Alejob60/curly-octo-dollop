import httpx
import asyncio
import json
import os
from loguru import logger

async def certify_master_flow():
    url_base = "http://localhost:8000/api/v1/pqrs"
    session_id = f"cert-master-emergency-{os.urandom(3).hex()}"
    
    print(f"\n🌪️ --- INICIANDO CERTIFICACIÓN MAESTRA (INTERINSTITUCIONAL): {session_id} ---")
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        # 1. ANALISIS INICIAL
        print("📥 PASO 1: Ingesta de Emergencia Rural (Escuela El Progreso)...")
        msg = ("Soy el rector del Colegio Rural El Progreso. Debido a las lluvias, la vía terciaria de acceso al colegio "
               "(Kilómetro 5 Vía La Cumbre) se ha derrumbado parcialmente. Hay un riesgo inminente de que la estructura "
               "del puente peatonal ceda. Además, hay filtraciones de aguas negras cerca de la cocina escolar que están "
               "enfermando a los niños con diarrea. Necesitamos maquinaria para la vía urgente y visita de salud pública para los niños.")
        
        res1 = await client.post(f"{url_base}/analyze", json={"session_id": session_id, "message": msg})
        print(f"   IA Status: {res1.json().get('cardType')} | Phase: {res1.json().get('phase', 'F1')}")

        # 2. CONFIRMAR IDENTIDAD
        print("🆔 PASO 2: Confirmando Identidad (Rector)...")
        slots_id = {
            "documento": "8106521",
            "nombres": "LUIS ALBERTO",
            "primer_apellido": "GARCIA",
            "segundo_apellido": "TORRES",
            "peticionario_tipo": "Representante Institucional"
        }
        await client.post(f"{url_base}/update-slot", json={"session_id": session_id, "slots": slots_id})

        # 3. CONFIRMAR CONTACTO
        print("📍 PASO 3: Ubicación de la Emergencia...")
        slots_contact = {
            "direccion": "Km 5 Vía La Cumbre - Corregimiento El Progreso",
            "celular": "3172272984",
            "email": "rectoria.progreso@educali.gov.co",
            "municipio": "Cali",
            "departamento": "Valle del Cauca"
        }
        await client.post(f"{url_base}/update-slot", json={"session_id": session_id, "slots": slots_contact})

        # 4. AUTORIZACIÓN Y FIRMA (Gatillo V51.0)
        print("⚖️ PASO 4: Firma de Emergencia y Consentimiento...")
        slots_auth = {"autorizacion_datos": True}
        res4 = await client.post(f"{url_base}/update-slot", json={"session_id": session_id, "slots": slots_auth})
        print(f"   Command: {res4.json().get('command')}")

        # 5. FINALIZACIÓN Y DOSSIER 1+N+N
        print("📄 PASO 5: Generando Dossier de Crisis (Multi-Dependencia)...")
        res5 = await client.post(f"{url_base}/finalize", json={"session_id": session_id})
        
        if res5.status_code == 200:
            result = res5.json()
            print(f"\n✅ CERTIFICACIÓN EXITOSA: {result['radicado_id']}")
            print(f"📚 Dossier de Crisis ({result['total_documents']} documentos):")
            for key, path in result['artifacts'].items():
                print(f"   - {key}: {path}")
        else:
            print(f"❌ FALLO CRÍTICO: {res5.status_code} - {res5.text}")

if __name__ == "__main__":
    asyncio.run(certify_master_flow())
