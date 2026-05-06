import asyncio
from google import genai
from google.genai import types
from app.core.config import settings

async def probe_regions():
    regions = ["us-central1", "us-east4", "us-west1", "europe-west1", "asia-northeast1"]
    model = "gemini-1.5-flash" # Use 1.5 for probing as it's more stable
    
    for region in regions:
        print(f"Probing {region}...")
        try:
            client = genai.Client(
                vertexai=True,
                project=settings.GCP_PROJECT_ID,
                location=region
            )
            response = client.models.generate_content(
                model=model,
                contents="ping"
            )
            print(f"✅ {region} is working. Quota available.")
        except Exception as e:
            print(f"❌ {region} failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(probe_regions())
