import httpx
import asyncio
import json

async def simulate_flow():
    url_analyze = "http://localhost:8000/api/v1/pqrs/analyze"
    url_update = "http://localhost:8000/api/v1/pqrs/update-slot"
    session_id = "sim-test-999"
    
    print("\n🚀 --- SIMULANDO PASO 1: ANALISIS INICIAL ---")
    payload1 = {"session_id": session_id, "message": "Hola soy Alejandro Garzon 123456789, quiero reportar un hueco."}
    async with httpx.AsyncClient() as client:
        res1 = await client.post(url_analyze, json=payload1)
        print(f"Respuesta IA: {res1.json().get('cardType')}")

        print("\n🚀 --- SIMULANDO PASO 2: CONFIRMAR CONTACTO ---")
        payload2 = {
            "session_id": session_id,
            "slots": {
                "email": "alejob600@gmail.com",
                "celular": "3146056358",
                "direccion": "Calle 47 # 13-4"
            }
        }
        res2 = await client.post(url_update, json=payload2)
        data2 = res2.json()
        print(f"¿Bucle detectado? Recibí: {data2.get('cardType')}")
        print(f"Fase en respuesta: {data2.get('phase')}")
        
        if data2.get('cardType') == "ContactCard":
            print("❌ FALLO: El sistema se quedó atrapado en el Paso 2.")
        elif data2.get('cardType') == "EvidenceAndLegalCard":
            print("✅ ÉXITO: El sistema avanzó al Paso 3.")
        else:
            print(f"❓ Resultado inesperado: {data2}")

if __name__ == "__main__":
    asyncio.run(simulate_flow())
