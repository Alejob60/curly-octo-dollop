import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        try:
            print("Sending request to backend...")
            response = await client.post(
                "http://127.0.0.1:8000/api/v1/multimodal/process-multimodal",
                data={"issue": "Tengo un problema con un hueco en la calle 5 con carrera 10.", "session_id": "test_session_real"},
                timeout=60.0
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
