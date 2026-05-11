import httpx
import asyncio
import json
import time
import sys

# Protocolo V65.3: Test de Estabilidad Diamond
BASE_URL = "http://localhost:8000/api/v1/pqrs"
SESSION_ID = f"test-diamond-{int(time.time())}"

async def run_test():
    print(f"💎 Iniciando Test de Estabilidad Orbital Prime V65.3")
    print(f"🆔 Sesión: {SESSION_ID}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. ANALYZE
        print("\n1. 🔍 Enviando Ingesta Inicial...")
        start_analyze = time.time()
        try:
            res = await client.post(f"{BASE_URL}/analyze", json={
                "session_id": SESSION_ID,
                "message": "Soy Eduardo Hurtado Sánchez, CC 123456789. Solicito capacitación en salud para la JAC Calimio."
            })
            print(f"   Status: {res.status_code} | Tiempo: {int(time.time() - start_analyze)}s")
            if res.status_code != 200: 
                print(f"   ❌ Error: {res.text}")
                return
        except Exception as e:
            print(f"   ❌ Fallo de conexión: {e}")
            print("   (Asegúrate de que 'uvicorn main:app' esté corriendo)")
            return
        
        # 2. UPDATE SLOT (Contacto)
        print("\n2. 📞 Sincronizando datos de contacto...")
        res = await client.post(f"{BASE_URL}/update-slot", json={
            "session_id": SESSION_ID,
            "slots": {
                "email": "eduardo.hurtado@cali.gov.co",
                "celular": "3157654321",
                "direccion": "Diagonal 71A # 26G - 20"
            }
        })

        # ⏳ ESPERAR A QUE LA IA TERMINE EL ANÁLISIS DE FONDO
        print("\n⏳ Esperando análisis de fondo (IA Judicial)...")
        for _ in range(30):
            await asyncio.sleep(2)
            p_res = await client.get(f"{BASE_URL}/progress/{SESSION_ID}")
            p_data = p_res.json()
            if p_data.get("analysis_ready") or p_data.get("progress", 0) >= 99:
                print(f"   ✅ IA Lista: {p_data.get('message')}")
                break
            print(f"   [{p_data.get('progress', 0)}%] {p_data.get('message')}")
        
        # 3. UPDATE SLOT (Confirmación Final)
        print("\n3. 🚀 Ejecutando Auto-Finalización por confirmación...")
        res = await client.post(f"{BASE_URL}/update-slot", json={
            "session_id": SESSION_ID,
            "slots": {
                "autorizacion_datos": True,
                "confirmado": True
            }
        })
        
        if res.status_code == 200:
            print(f"   Status: {res.status_code} | Card: {res.json().get('cardType')}")
        else:
            print(f"   ❌ Error en Finalize: {res.text}")
            return
        
        # 4. POLLING DE PROGRESO
        print("\n4. ⏳ Monitoreando Bóveda Digital (Polling)...")
        start_time = time.time()
        for i in range(20):
            await asyncio.sleep(3)
            p_res = await client.get(f"{BASE_URL}/progress/{SESSION_ID}")
            data = p_res.json()
            
            status = data.get("status")
            progress = data.get("progress", 0)
            msg = data.get("message", "Generando expediente...")
            
            print(f"   [{int(time.time() - start_time)}s] Progreso: {progress}% | {msg}")
            
            if status == "complete" or progress == 100:
                print("\n✅ ¡FLUJO DIAMOND COMPLETADO EXITOSAMENTE!")
                print(f"🏛️ Radicado: {data.get('radicado_id')}")
                print("📂 Documentos en Bóveda:")
                for doc in data.get('documents', []):
                    print(f"   - {doc['type'].upper()}: {doc['url']}")
                break
            
            if status == "error":
                print(f"\n❌ ERROR EN EL FLUJO: {data.get('message')}")
                break
        else:
            print("\n❌ TIMEOUT: La generación tardó demasiado.")

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\nTest cancelado por el usuario.")
