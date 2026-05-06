import httpx
import asyncio
import json
import hashlib
import time

BASE_URL = "http://localhost:8000/api/v1/pqrs"
SESSION_ID = f"test-salud-{int(time.time())}"

async def run_test():
    print(f"🚀 Iniciando Test E2E para Sesión: {SESSION_ID}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. ANALYZE
        print("\n1. Enviando mensaje inicial (Deep Analysis)...")
        start_analyze = time.time()
        res = await client.post(f"{BASE_URL}/analyze", json={
            "session_id": SESSION_ID,
            "message": "Solicitamos jornada de capacitación en manipulación de alimentos para el 24 de octubre de 2025, 2:00-4:00 PM. Representante: Eduardo Hurtado Sánchez, JAC Calimio Decepaz."
        })
        print(f"Response: {res.status_code} | Time: {int(time.time() - start_analyze)}s")
        if res.status_code != 200: 
            print(f"❌ Error Analyze: {res.text}")
            return
        
        # 2. UPDATE SLOT (Identidad)
        print("\n2. Completando Identidad...")
        res = await client.post(f"{BASE_URL}/update-slot", json={
            "session_id": SESSION_ID,
            "slots": {
                "documento": "123456789",
                "nombres": "Eduardo",
                "apellidos": "Hurtado Sánchez"
            }
        })
        
        # 3. UPDATE SLOT (Contacto)
        print("\n3. Completando Contacto...")
        res = await client.post(f"{BASE_URL}/update-slot", json={
            "session_id": SESSION_ID,
            "slots": {
                "email": "test@cali.gov.co",
                "celular": "3001234567",
                "direccion": "Calle 123 #45-67"
            }
        })
        
        # 4. UPDATE SLOT (Confirmación Final)
        print("\n4. Enviando Confirmación de Fase 4...")
        res = await client.post(f"{BASE_URL}/update-slot", json={
            "session_id": SESSION_ID,
            "slots": {
                "autorizacion_datos": True,
                "confirmed": True,
                "confirmado": True
            }
        })
        print(f"Status: {res.status_code} | Card: {res.json().get('cardType')}")
        
        # 5. POLLING DE PROGRESO
        print("\n5. Iniciando Polling de Generación...")
        start_time = time.time()
        for _ in range(30):
            await asyncio.sleep(3)
            p_res = await client.get(f"{BASE_URL}/progress/{SESSION_ID}")
            data = p_res.json()
            status = data.get("status")
            progress = data.get("progress", 0)
            msg = data.get("message", "")
            
            print(f"[{int(time.time() - start_time)}s] Status: {status} | Progress: {progress}% | Msg: {msg}")
            
            if status == "complete":
                print("\n✅ ¡FLUJO COMPLETADO EXITOSAMENTE!")
                print(f"Radicado: {data.get('data', {}).get('radicado_id')}")
                print("Documentos Generados:")
                for doc in data.get('data', {}).get('documents', []):
                    print(f"  - {doc['type']}: {doc['preview_url']}")
                break
            
            if status == "error":
                print(f"\n❌ ERROR EN BACKEND: {data.get('message')}")
                break
        else:
            print("\n❌ TIMEOUT: El proceso demoró más de 90 segundos.")

if __name__ == "__main__":
    asyncio.run(run_test())
