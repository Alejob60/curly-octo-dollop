import json
from typing import Any, Dict, List

from loguru import logger

from app.core.azure_openai_client import get_azure_openai_client
from app.core.config import settings
from app.core.vector_store import vector_store
from app.services.document_ai import document_ai


class JudicialParserService:
    def __init__(self):
        self.client = get_azure_openai_client()
        self.model = settings.AI_CHAT_MODEL

    @staticmethod
    def _clean_json(response_text: str) -> Dict[str, Any]:
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)

    @staticmethod
    def _is_favorable_outcome(outcome: str) -> bool:
        normalized = (outcome or "").strip().lower()
        favorable_markers = [
            "favorable",
            "accede",
            "concede",
            "ampara",
            "ganado",
            "estimatoria",
            "procede",
        ]
        return any(token in normalized for token in favorable_markers)

    async def _estimate_success_probability(self, summary: str, precedent_cases: List[dict]) -> float:
        if not precedent_cases:
            return 0.5

        favorable = sum(1 for c in precedent_cases if self._is_favorable_outcome(c.get("outcome", "")))
        historical_ratio = favorable / max(len(precedent_cases), 1)

        prompt = f"""
        Eres un analista judicial. Con base en este resumen de demanda y el ratio historico,
        devuelve solo un numero entre 0 y 1 como probabilidad de exito para el demandante.

        Resumen:
        {summary}

        Ratio historico favorable:
        {historical_ratio}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=20,
                temperature=0,
            )
            raw = (response.choices[0].message.content or "0.5").strip().replace(",", ".")
            ai_score = float(raw)
            ai_score = min(max(ai_score, 0.0), 1.0)
            return round((ai_score + historical_ratio) / 2, 4)
        except Exception as exc:
            logger.warning(f"No fue posible calcular score por IA, usando historial: {exc}")
            return round(historical_ratio, 4)

    async def parse_demand_pdf(self, file_bytes: bytes, case_type: str = "JUDICIAL_DEMAND") -> Dict[str, Any]:
        text = document_ai._extract_text_from_pdf(file_bytes)
        if not text:
            raise ValueError("No se pudo extraer texto del PDF judicial")

        prompt = f"""
        Analiza el siguiente texto de una demanda judicial colombiana y responde en JSON estricto.

        Esquema exacto:
        {{
          "summary": "resumen breve en 3-5 lineas",
          "pretensiones": [{{"concept": "...", "amount": 0, "currency": "COP"}}],
          "partes": [{{"role": "demandante|demandado|tercero", "name": "...", "id_number": "... o null"}}],
          "pruebas_aportadas": ["lista de pruebas detectadas"]
        }}

        Reglas:
        - Si no existe monto, usar null en amount.
        - No inventes partes ni pruebas.
        - Responder solo JSON.

        Texto demanda:
        {text[:18000]}
        """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=2500,
            temperature=0,
        )
        parsed = self._clean_json(response.choices[0].message.content or "{}")

        summary = parsed.get("summary", "")
        precedents = await vector_store.search_similar_cases(
            query_text=f"{case_type}\n{summary}\n{text[:1500]}",
            limit=5,
        )
        success_probability = await self._estimate_success_probability(summary, precedents)

        return {
            "summary": summary,
            "pretensiones": parsed.get("pretensiones", []),
            "partes": parsed.get("partes", []),
            "pruebas_aportadas": parsed.get("pruebas_aportadas", []),
            "probabilidad_exito": success_probability,
            "precedentes_similares": precedents,
        }


judicial_parser_service = JudicialParserService()
