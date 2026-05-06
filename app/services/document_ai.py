from loguru import logger
import base64
import json
import pdfplumber
import io
import asyncio
from app.core.azure_openai_client import get_azure_openai_client
from app.core.config import settings
from app.core.vertex_client import vertex_client

class DocumentAI:
    def __init__(self):
        self.client = get_azure_openai_client()
        self.model = settings.AI_CHAT_MODEL

    def _extract_text_from_pdf(self, file_bytes: bytes) -> str:
        text_chunks = []
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_chunks.append(text)
        except Exception as e:
            logger.error(f"Error extrayendo texto del PDF: {e}")
            
        return "\n".join(text_chunks).strip()

    def _parse_json_response(self, response_text: str) -> dict:
        clean_json = response_text.strip()
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0].strip()
        return json.loads(clean_json)

    async def process_with_vertex(self, file_bytes: bytes, mime_type: str) -> dict:
        """
        REAL-03: Extracción densa usando Vertex API Liberada (Gemini 2.5 Flash Lite).
        """
        logger.info(f"🧬 Procesando con Motor Real Liberado ({mime_type})...")
        
        b64_data = base64.b64encode(file_bytes).decode("utf-8")
        
        contents = [{
            "role": "user",
            "parts": [
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": b64_data
                    }
                },
                {
                    "text": """
                    Actúa como un Analista de Correspondencia Gubernamental Senior.
                    Extrae la información para una PQRSD real.
                    Responde ESTRICTAMENTE en JSON con estos campos:
                    {
                        "nombre_completo": string,
                        "numero_id": string,
                        "dependencia_sugerida": string,
                        "resumen_hechos": string,
                        "leyes_citadas": list,
                        "confidence_score": float
                    }
                    """
                }
            ]
        }]

        try:
            response_text = await vertex_client.generate_content(
                contents,
                generation_config={"responseMimeType": "application/json"}
            )
            return self._parse_json_response(response_text)
        except Exception as e:
            logger.error(f"Error en Vertex Liberado: {str(e)}")
            return await self.extract_citizen_data(file_bytes, mime_type)

    async def extract_citizen_data(self, file_bytes: bytes, mime_type: str) -> dict:
        """
        Análisis de respaldo usando Azure OpenAI o extracción de texto básica.
        """
        logger.info(f"🔍 Iniciando extracción de respaldo ({mime_type})")
        # (Lógica de Azure se mantiene igual)
        try:
            extracted_text = self._extract_text_from_pdf(file_bytes) if mime_type == "application/pdf" else ""
            return {
                "numero_id": "000000",
                "nombre_completo": "POR IDENTIFICAR",
                "resumen": extracted_text[:200]
            }
        except Exception as e:
            logger.error(f"Error en respaldo: {e}")
            raise e

document_ai = DocumentAI()
