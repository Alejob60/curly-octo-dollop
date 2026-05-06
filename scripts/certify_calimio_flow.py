import httpx
import asyncio
import json
import os
from loguru import logger

async def certify_flow():
    url_base = "http://localhost:8000/api/v1/pqrs"
    session_id = f"cert-calimio-{os.urandom(3).hex()}"
    
    print(f"\n🚀 --- INICIANDO CERTIFICACIÓN FORENSE: {session_id} ---")
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        # 1. ANALISIS INICIAL
        print("📥 PASO 1: Ingesta de Solicitud JAC...")
        msg = "EL SEÑOR EDUARDO HURTADO SANCHEZ DE LA JUNTA DE ACCIÓN COMUNAL DE CALIMIO DECEPAZ, SOLICITA UNA JORNADA DE CAPACITACIÓN Y CERTIFICACIÓN DE MANIPULACIÓN DE ALIMENTOS, PARA EL DÍA 24 DE OCTUBRE 2025, HORA 2:00 PM A 4:00PM."
        res1 = await client.post(f"{url_base}/analyze", json={"session_id": session_id, "message": msg})
        print(f"   IA Response: {res1.json().get('cardType')}")

        # 2. CONFIRMAR IDENTIDAD (Slot Filling)
        print("🆔 PASO 2: Confirmando Identidad...")
        slots_id = {
            "documento": "10300452",
            "nombres": "EDUARDO",
            "primer_apellido": "HURTADO",
            "segundo_apellido": "SANCHEZ",
            "peticionario_tipo": "Representante JAC"
        }
        await client.post(f"{url_base}/update-slot", json={"session_id": session_id, "slots": slots_id})

        # 3. CONFIRMAR CONTACTO
        print("📍 PASO 3: Confirmando Ubicación y Contacto...")
        slots_contact = {
            "direccion": "Sector Rural Calimio Decepaz",
            "celular": "3146056358",
            "email": "eduardo.hurtado@gmail.com",
            "municipio": "Cali",
            "departamento": "Valle del Cauca"
        }
        await client.post(f"{url_base}/update-slot", json={"session_id": session_id, "slots": slots_contact})

        # 4. AUTORIZACIÓN Y FIRMA (Gatillo de Phase 4)
        print("⚖️ PASO 4: Autorizando Habeas Data...")
        slots_auth = {"autorizacion_datos": True}
        res4 = await client.post(f"{url_base}/update-slot", json={"session_id": session_id, "slots": slots_auth})
        print(f"   Status: {res4.json().get('command')}")

        # 5. FINALIZACIÓN Y GENERACIÓN DE DOSSIER 1+N+N
        print("📄 PASO 5: Generando Dossier Administrativo Completo...")
        res5 = await client.post(f"{url_base}/finalize", json={"session_id": session_id})
        
        if res5.status_code == 200:
            result = res5.json()
            print(f"\n✅ CERTIFICACIÓN EXITOSA: {result['radicado_id']}")
            print(f"📚 Documentos generados ({result['total_documents']}):")
            for key, path in result['artifacts'].items():
                print(f"   - {key}: {path}")
        else:
            print(f"❌ FALLO CRÍTICO: {res5.status_code} - {res5.text}")

if __name__ == "__main__":
    asyncio.run(certify_flow())
