import re
import os
from typing import Dict, Any, Optional
from loguru import logger
from app.core.vertex_client import vertex_client
from pydantic import BaseModel

class LawClassification(BaseModel):
    law_id: str
    confidence: float
    reason: str

class LawRouter:
    """
    💎 MÓDULO 4: ENRUTADOR LEGAL (V65.7)
    Clasificador dinámico y mapeador de estrategias legales.
    """
    
    def __init__(self):
        self.prompt_dir = "prompts/laws/"
        # Mapeo rápido por palabras clave (Regex)
        self.keywords = {
            "ley_1437": [r"recurso", r"apelación", r"reposición", r"administrativo"],
            "ley_1755": [r"petición", r"información", r"queja", r"reclamo"]
        }

    async def classify(self, text: str) -> LawClassification:
        """Detección híbrida: Regex + LLM Ligero"""
        # 1. Intento por Regex
        text_lower = text.lower()
        for law_id, patterns in self.keywords.items():
            if any(re.search(pat, text_lower) for pat in patterns):
                logger.info(f"⚖️ [LAW_ROUTER] Clasificación Regex: {law_id}")
                return LawClassification(law_id=law_id, confidence=0.8, reason="Keyword match")

        # 2. Refinamiento con IA
        try:
            prompt = f"""
            Clasifica la siguiente solicitud ciudadana en una de estas categorías legales:
            - ley_1755: Derecho de Petición general.
            - ley_1437: Recursos contra actos administrativos.
            - ley_generica: Otras solicitudes.
            
            TEXTO: {text[:500]}
            
            Responde SOLO con el ID de la ley.
            """
            ai_resp = await vertex_client.generate_content([prompt])
            law_id = ai_resp.strip().lower()
            
            valid_ids = ["ley_1755", "ley_1437", "ley_generica"]
            final_id = law_id if law_id in valid_ids else "ley_1755"
            
            return LawClassification(law_id=final_id, confidence=0.9, reason="AI classification")
        except Exception as e:
            logger.error(f"❌ Fallo en clasificación IA: {e}")
            return LawClassification(law_id="ley_1755", confidence=0.5, reason="Fallback")

    def get_template(self, law_id: str) -> str:
        """Carga el template específico para la ley detectada"""
        file_path = os.path.join(self.prompt_dir, f"{law_id}.txt")
        if not os.path.exists(file_path):
            file_path = os.path.join(self.prompt_dir, "ley_1755.txt")
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"❌ Error cargando template legal: {e}")
            return "OBJETIVO: Procesamiento general."

law_router = LawRouter()
