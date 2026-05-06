from typing import Dict, Any, Protocol
from app.schemas.ingestion import GovDocsPayload
from loguru import logger
import hashlib
import json
import re

class SourceAdapter(Protocol):
    def normalize(self, raw_data: Dict[str, Any]) -> GovDocsPayload:
        ...

class UniversalAdapter:
    def __init__(self):
        # Mapeos básicos para sistemas conocidos
        pass

    def detect_priority(self, content: str) -> str:
        """Detecta si el contenido es una Tutela o Desacato para priorización."""
        critical_keywords = [r"tutela", r"desacato", r"derecho fundamental", r"medida cautelar", r"arresto"]
        content_lower = content.lower()
        
        for kw in critical_keywords:
            if re.search(kw, content_lower):
                return "HIGH"
        return "NORMAL"

    def process(self, source_type: str, data: Dict[str, Any]) -> GovDocsPayload:
        # Lógica de normalización (simplificada para el ejemplo, manteniendo la estructura anterior)
        content = data.get("content") or data.get("TX_BODY") or data.get("texto_solicitud") or ""
        
        priority = self.detect_priority(content)
        
        # Estandarización inspirada en IBM Sterling
        normalized = GovDocsPayload(
            external_id=str(data.get("external_id") or data.get("radicado_nro") or data.get("VB_IDENT")),
            source_system=source_type,
            citizen_name=data.get("citizen_name") or data.get("remitente", "ANÓNIMO"),
            citizen_id=data.get("citizen_id") or data.get("identificacion", "N/A"),
            citizen_email=data.get("citizen_email") or data.get("email", "no-reply@cali.gov.co"),
            content=content,
            category="TUTELA" if priority == "HIGH" else "PQRSD",
            metadata={
                "detected_priority": priority,
                "needs_immediate_action": priority == "HIGH"
            }
        )
        
        if priority == "HIGH":
            logger.warning(f"🚨 ALERTA CRÍTICA: Se ha detectado una TUTELA/DESACATO en el radicado {normalized.external_id}")
            
        return normalized

    @staticmethod
    def calculate_checksum(data: Dict[str, Any]) -> str:
        dumped = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(dumped).hexdigest()

bridge_adapter = UniversalAdapter()
