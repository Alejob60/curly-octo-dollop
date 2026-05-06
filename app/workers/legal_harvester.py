import httpx
import fitz
from loguru import logger
import json
import asyncio
from app.core.azure_openai_client import get_async_azure_openai_client
from app.core.config import settings
from app.core.db_clients import AsyncSessionLocal
from app.core.vector_store import vector_store
from sqlalchemy import text

class LegalHarvester:
    def __init__(self):
        self.client = get_async_azure_openai_client()
        self.model = settings.AI_CHAT_MODEL

    async def extract_and_analyze(self, url: str):
        logger.info(f"🔎 Analizando fuente legal: {url}")
        
        # Simulación de extracción de texto de PDF (Ya implementado anteriormente)
        raw_text = """
            RESOLUCIÓN DE HACIENDA 2024. Se niega la reliquidación de cesantías al docente 
            por prescripción del derecho conforme al Decreto 1234. El término de 3 años 
            se cumplió sin interrupción del término.
        """
        
        # PROMPT ESPECÍFICO PARA CESANTÍAS
        prompt = f"""
        Analiza este documento de la Alcaldía de Cali. 
        Si trata sobre RELIQUIDACIÓN DE CESANTÍAS, extrae el argumento técnico exacto para negar o conceder.
        
        TEXTO: {raw_text}
        
        Responde en JSON:
        {{
            "is_cesantias": true/false,
            "type": "TUTELA/RESOLUCION",
            "outcome": "FAVORABLE/DESFAVORABLE",
            "golden_argument": "...",
            "legal_base": "Artículos citados"
        }}
        """
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=1200,
        )
        response_text = response.choices[0].message.content or "{}"
        wisdom = json.loads(response_text.replace('```json', '').replace('```', '').strip())
        
        if wisdom.get("is_cesantias"):
            logger.warning(f"🎯 [HARVESTER] ¡Precedente de Cesantías capturado!: {url}")
        
        # Guardar en el cerebro vectorial (Postgres)
        await self.save_to_db(wisdom, url)

    async def save_to_db(self, wisdom, url):
        embedding = vector_store.get_embedding(wisdom["golden_argument"])
        async with AsyncSessionLocal() as session:
            async with session.begin():
                query = text("""
                    INSERT INTO legal_precedents (case_type, decision_outcome, legal_argument, source_url, embedding)
                    VALUES (:ctype, :out, :arg, :url, :emb::vector)
                """)
                await session.execute(query, {
                    "ctype": wisdom["type"], "out": wisdom["outcome"],
                    "arg": wisdom["golden_argument"], "url": url, "emb": str(embedding)
                })
        logger.info(f"✅ Sabiduría indexada: {wisdom['type']}")

harvester = LegalHarvester()
