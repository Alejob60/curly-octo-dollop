import httpx
import asyncio
import json

async def test():
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                "http://localhost:8080/api/v1/pqrs/submit", 
                json={
                    "asunto": "Solicitud Capacitación", 
                    "descripcion": "Solicito jornada de capacitación en manipulación de alimentos para la JAC Calimio.",
                    "identificacion": "CC12345678"
                }
            )
            print(f"Status: {res.status_code}")
            print(f"Body: {res.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
