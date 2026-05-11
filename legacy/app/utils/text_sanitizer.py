import re
from typing import Dict, Any

TOKENIZATION_FIXES = {
    r'Le\s+y': 'Ley', r'p\s+ersonal': 'personal', r'ca\s+pacitación': 'capacitación',
    r'hi\s+giénicas': 'higiénicas', r'mani\s+pulador': 'manipulador',
    r'p\s+rácticas': 'prácticas', r'o\s+portuno': 'oportuno',
    r'Com\s+prende': 'Comprende', r'ex\s+puesto': 'expuesto',
    r'com\s+petente': 'competente', r'res\s+puesta': 'respuesta',
    r'diri\s+ge': 'dirige', r'correspo\s+ndiente': 'correspondiente',
    r'CAPA\s+CITA\s+CION': 'CAPACITACION', r'incompe\s+tente': 'incompetente',
    r'p\s+or': 'por', r'qu\s+ien': 'quien', r'ba\s+jo': 'bajo',
    r'g\s+roundin\s+g': 'grounding', r'le\s+g\s+al': 'legal',
    r'p\s+rofundidad': 'profundidad', r'su\s+tancia': 'sustancia',
    r'Lo\s+gística': 'Logística', r'Re\s+QUERIMIENTOS': 'REQUERIMIENTOS',
    r'si\s+guientes': 'siguientes', r'p\s+ara': 'para',
    r'pe\s+tición': 'petición', r'Princi\s+p\s+ios': 'Principios',
    r'im\s+p\s+arcialidad': 'imparcialidad', r'p\s+ublicidad': 'publicidad'
}

NAME_FIXES = {"edurado": "Eduardo", "huratado": "Hurtado", "sanhez": "Sánchez"}

def fix_tokenization(text: str) -> str:
    if not text or not isinstance(text, str): return ""
    for pattern, replacement in TOKENIZATION_FIXES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text.strip()

def normalize_name(name: str) -> str:
    if not name: return ""
    name = name.lower().strip()
    for wrong, right in NAME_FIXES.items():
        if wrong in name: name = name.replace(wrong, right)
    return ' '.join(w.capitalize() for w in name.split())

def validate_and_clean_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Valida y limpia contexto antes de generar PDFs"""
    clean = ctx.copy()
    
    # Sanitizar textos
    for k in ["nombres", "apellidos", "hechos_extraidos", "borrador_proyeccion", "motivo", "asunto"]:
        if k in clean:
            if isinstance(clean[k], str):
                clean[k] = fix_tokenization(clean[k])
            elif isinstance(clean[k], list):
                clean[k] = [fix_tokenization(i) if isinstance(i, str) else i for i in clean[k]]
    
    # Normalizar nombres
    if clean.get("nombres"): clean["nombres"] = normalize_name(clean["nombres"])
    if clean.get("apellidos"): clean["apellidos"] = normalize_name(clean["apellidos"])
    
    # Fallback para hechos vacíos
    hechos = str(clean.get("hechos_extraidos", ""))
    if not hechos or len(hechos) < 20 or "no se extrajeron" in hechos.lower():
        motivo = clean.get("motivo", "")
        clean["hechos_extraidos"] = f"El ciudadano solicita el trámite basándose en el motivo: {fix_tokenization(motivo[:300])}" if motivo else "Solicitud de trámite administrativo estándar."
    
    # Fallback para citas vacías
    if not clean.get("citas_verificables"):
        clean["citas_verificables"] = [
            {"citacion_formato": "Ley 1755 de 2015", "articulo": "13", "texto_relevante": "Derecho fundamental de petición.", "ente_emisor": "Congreso de la República"}
        ]
    
    return clean
