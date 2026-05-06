from app.services.legal_agents.state import LegalCaseState
from app.core.vertex_client import vertex_client
from datetime import datetime, timedelta
import json
import re

class FactExtractorAgent:
    async def validate_input(self, state: LegalCaseState) -> bool:
        return len(state.raw_input) > 20
    
    async def execute(self, state: LegalCaseState) -> dict:
        text_lower = state.raw_input.lower()
        # Detección de infraestructura para exigencia de ubicación
        is_infra = any(kw in text_lower for kw in ["derrumbe", "vía", "calzada", "puente", "bache", "deslizamiento", "pavimento"])
        
        prompt = f"""
        ERES UN EXTRACTOR DE HECHOS LEGALES DE LA ALCALDÍA DE CALI.
        Extrae la información del ciudadano y los hechos del mensaje (RESPONDE SOLO JSON).

        TEXTO: {state.raw_input}
        
        INSTRUCCIONES DE JERARQUÍA SEMÁNTICA:
        1. IDENTIFICAR PROBLEMA vs UBICACIÓN: "Derrumbe cerca de la escuela" -> Problema: DERRUMBE (Infraestructura).
        2. PRIORIZAR RIESGO FÍSICO: Si hay palabras como "derrumbe" o "peligro", el caso es de INFRAESTRUCTURA/GESTIÓN RIESGO, no de Educación.
        
        CAMPOS OBLIGATORIOS:
        - facts: Lista de hechos cronológicos claros (mínimo 3).
        - nombres: Solo los nombres.
        - apellidos: Solo los apellidos.
        - documento: CC/NIT.
        - incident_location: UBICACIÓN EXACTA DEL PROBLEMA (Sector, Vereda, Cra/Calle, Coordenadas). ⚠️ VITAL SI HAY RIESGO.
        - email, celular, direccion: Datos del peticionario.
        - urgency: true si hay peligro físico.
        
        FORMATO JSON: 
        {{
          "facts": ["..."], "nombres": "...", "apellidos": "...", "documento": "...",
          "incident_location": "...", "email": "...", "celular": "...", "direccion": "...", "urgency": false
        }}
        """
        
        res = await vertex_client.generate_content([prompt])
        clean = re.sub(r'```json|```', '', res).strip()
        try:
            import json_repair
            data = json_repair.loads(clean)
            if isinstance(data, list): data = data[0] if data else {}
        except:
            data = {}
            
        return {
            "facts": data.get("facts", []),
            "nombres": data.get("nombres"),
            "apellidos": data.get("apellidos"),
            "documento": data.get("documento"),
            "incident_location": data.get("incident_location", ""),
            "email": data.get("email", ""),
            "celular": data.get("celular", ""),
            "direccion": data.get("direccion", ""),
            "deadline": (datetime.utcnow() + timedelta(days=15)).isoformat(),
            "rights_invoked": data.get("rights_invoked", []),
            "is_infrastructure": is_infra
        }
