import re
import json
from typing import Dict, Any, List
from datetime import datetime

class PDFSanitizer:
    @staticmethod
    def fix_tokenization(text: str) -> str:
        if not text: return ""
        # 🔧 FIX 1: Patrones corregidos sin espacios erróneos (Diamond Quality)
        patterns = {
            r'Le\s+y': 'Ley', r'p\s+ersonal': 'personal', r'ca\s+pacitación': 'capacitación',
            r'hi\s+giénicas': 'higiénicas', r'mani\s+pulador': 'manipulador',
            r'p\s+rácticas': 'prácticas', r'o\s+portuno': 'oportuno',
            r'Com\s+prende': 'Comprende', r'ex\s+puesto': 'expuesto',
            r'com\s+petente': 'competente', r'res\s+puesta': 'respuesta',
            r'diri\s+ge': 'dirige', r'correspo\s+ndiente': 'correspondiente',
            r'CAPA\s+CITA\s+CION': 'CAPACITACION', r'Lu\s+g\s+ar': 'Lugar',
            r'Cu\s+p\s+os': 'Cupos', r'E\s+q\s+uipos': 'Equipos',
            r'instru\s+y\s+e': 'instruye', r'p\s+edagógi\s+cos': 'pedagógicos',
            r'cum\s+p\s+limiento': 'cumplimiento', r'si\s+guientes': 'siguientes',
            r'Refri\s+gerios': 'Refrigerios', r'Im\s+presión': 'Impresión',
            r'Bóveda\s+Di\s+gital': 'Bóveda Digital', r'Códi\s+g\s+o': 'Código',
            r'p\s+or': 'por', r'p\s+ersona': 'persona', r'p\s+ronta': 'pronta',
            r'g\s+arantizando': 'garantizando', r'es\s+pecializado': 'especializado'
        }
        for pat, rep in patterns.items():
            text = re.sub(pat, rep, text, flags=re.IGNORECASE)
        return text.strip()

    @staticmethod
    def strip_ai_metadata(text: str) -> str:
        """🔧 FIX 2: Eliminar metadata de IA y auditoría interna de los documentos oficiales."""
        if not text or not isinstance(text, str): return text
        # Eliminar bloques de certificación IA y telemetría
        ai_sections = [
            r'IV\.\s*CERTIFICACIÓN.*?(?=\n\n|$)',
            r'Score de Calidad.*?\n.*?\n',
            r'Verificado\s+p?or\s+Gemini.*?\n',
            r'SISTEMA ORBITAL PRIME.*?\n',
            r'Motor Judicial.*?\n'
        ]
        for sec in ai_sections:
            text = re.sub(sec, '', text, flags=re.DOTALL | re.IGNORECASE)
        return text.strip()

    @staticmethod
    def inject_context(context: Dict[str, Any]) -> Dict[str, Any]:
        safe = context.copy()
        now = datetime.now()
        
        # 1. Reemplazar placeholders por datos reales o fallback seguro
        placeholders = {
            "[NOMBRE_1]": safe.get("nombres", "Peticionario"),
            "[ID_1]": safe.get("documento", "XXX"),
            "[CELULAR_1]": safe.get("celular", "XXX"),
            "[EMAIL_1]": safe.get("email", "XXX"),
            "[DIRECCION_1]": safe.get("direccion", "XXX"),
            "[FECHA_RADICADO]": now.strftime("%d/%m/%Y"),
            "[FECHA_ACTUAL]": now.strftime("%d de %B de %Y")
        }
        for key in ["borrador_proyeccion", "hechos_extraidos", "soporte_traslado", "asunto"]:
            if safe.get(key):
                for ph, val in placeholders.items():
                    safe[key] = str(safe[key]).replace(ph, str(val))
                safe[key] = PDFSanitizer.fix_tokenization(safe[key])
        
        # 2. Validar y limpiar citas
        if isinstance(safe.get("citas_verificables"), str):
            try: safe["citas_verificables"] = json.loads(safe["citas_verificables"])
            except: safe["citas_verificables"] = []
            
        if not safe.get("citas_verificables") or not isinstance(safe.get("citas_verificables"), list):
            safe["citas_verificables"] = [{
                "citacion_formato": "Ley 1755 de 2015", "articulo": "13",
                "texto_relevante": "Toda persona tiene derecho a presentar peticiones respetuosas a las autoridades y a obtener pronta resolución.",
                "ente_emisor": "Congreso de la República"
            }]
            
        for cita in safe["citas_verificables"]:
            if isinstance(cita, dict):
                for k in ["citacion_formato", "texto_relevante", "ente_emisor"]:
                    if cita.get(k): cita[k] = PDFSanitizer.fix_tokenization(cita[k])
                    
        return safe
