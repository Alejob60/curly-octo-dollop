import httpx
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from loguru import logger
import json
import asyncio
from app.core.azure_openai_client import get_async_azure_openai_client
from app.core.config import settings
from app.core.db_clients import AsyncSessionLocal
from app.core.vector_store import vector_store
from sqlalchemy import text

class LegalScraper:
    def __init__(self):
        self.client = get_async_azure_openai_client()
        self.model = settings.AI_CHAT_MODEL

    async def extract_wisdom_from_text(self, text_content: str):
        """Usa IA para extraer el argumento legal ganador de un texto largo."""
        prompt = f"""
        Analiza la siguiente sentencia o documento legal de la Alcaldía de Cali.
        Extrae:
        1. Tipo de caso (TUTELA, DERECHO_PETICION, etc)
        2. Resultado (FAVORABLE, DESFAVORABLE)
        3. Argumento Central (La razón jurídica por la que se ganó o perdió).
        
        Responde estrictamente en formato JSON:
        {{
            "type": "tipo",
            "outcome": "resultado",
            "argument": "resumen del argumento legal"
        }}
        
        TEXTO:
        {text_content[:15000]}  # Limitamos para no exceder tokens
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=1200,
            )
            response_text = response.choices[0].message.content or "{}"
            # Limpiar posibles bloques de código markdown
            json_str = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Error extrayendo sabiduría con IA: {str(e)}")
            return None

    async def scrape_and_index(self, url: str):
        """Simula el proceso de descarga, lectura e indexación."""
        logger.info(f"🕸️ Explorando fuente: {url}")
        
        # Simulación de descarga de PDF y extracción de texto
        # En un escenario real, usaríamos httpx.get(url) y fitz.open(stream)
        mock_text = """
            SENTENCIA DE TUTELA SEGUNDA INSTANCIA. El Juzgado 5to de Cali confirma fallo a favor 
            de la Alcaldía. El ciudadano solicitaba pavimentación inmediata, pero la Secretaría 
            de Infraestructura demostró que la obra ya está en el presupuesto del próximo año. 
            Se declara Hecho Superado por planeación administrativa.
        """
        
        wisdom = await self.extract_wisdom_from_text(mock_text)
        
        if wisdom:
            logger.success(f"⚖️ Sabiduría extraída: {wisdom['type']} - {wisdom['outcome']}")
            
            # Guardar en la base de datos con el campo source_url
            embedding = vector_store.get_embedding(wisdom["argument"])
            
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    query = text("""
                        INSERT INTO legal_precedents (case_type, decision_outcome, legal_argument, source_url, embedding)
                        VALUES (:ctype, :out, :arg, :url, :emb::vector)
                    """)
                    await session.execute(query, {
                        "ctype": wisdom["type"],
                        "out": wisdom["outcome"],
                        "arg": wisdom["argument"],
                        "url": url,
                        "emb": str(embedding)
                    })
            return True
        return False

scraper = LegalScraper()

if __name__ == "__main__":
    # Test rápido
    async def test():
        await scraper.scrape_and_index("https://www.cali.gov.co/juridica/gacetas/2025")
    asyncio.run(test())
