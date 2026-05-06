import re
import json
from loguru import logger
from typing import Dict, Any

class DeterministicEntityExtractor:
    """
    ARCH-1.3: Extractor determinístico de entidades.
    Reemplaza la incertidumbre del LLM con reglas y regex para datos críticos.
    """
    
    PATTERNS = {
        "cc": r"(?:CC|NIT|ID|Documento|Identificación)[:\s\-]+(?:[a-zA-Z\s]+)?(\d{7,15})",
        "email": r"(?:Email|correo)[:\s\-]+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
        "telefono": r"(?:Celular|teléfono|tel)[:\s\-]+(\d{10})",
        "direccion": r"(?:Dirección|ubicación|en Cali)[:\s\-]+([^.\n\r]+)",
        "placa": r"(?:Placa|vehículo)[:\s\-]+([A-Z]{3}[0-9]{2,3}[A-Z]?)",
    }

    def extract(self, text: str) -> Dict[str, Any]:
        """Extrae entidades con 100% de consistencia."""
        results = {}
        for entity, pattern in self.PATTERNS.items():
            match = re.search(pattern, text, re.I | re.M)
            if match:
                val = match.group(1).strip().rstrip(".,") # Limpieza profunda
                # Validación mínima de calidad
                if entity == "cc" and len(val) < 7: continue
                results[entity] = val
        
        # Rescate de nombres (NER rule-based simple)
        if "Peticionario:" in text or "Nombre:" in text:
            name_match = re.search(r"(?:Peticionario|Nombre)[:\s\-]+([a-zA-Z\s]+?)(?=\s*(?:CC|NIT|Email|Dirección|,|\.|\n|$))", text, re.I)
            if name_match:
                results["nombre_completo"] = name_match.group(1).strip()

        logger.debug(f"🔒 Extracción Determinística: {results}")
        return results

deterministic_extractor = DeterministicEntityExtractor()
