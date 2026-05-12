import json, logging
from datetime import date, datetime
from typing import Tuple, List

logger = logging.getLogger(__name__)

# Lista negra de placeholders (Requerimiento Usuario)
PLACEHOLDERS = ["123456789", "equipo técnico", "50 personas", "cc 123456789", "por definir"]

def validate_legal_json(legal_json: dict, radicado: str, original_payload: dict) -> Tuple[bool, List[str]]:
    """
    🛡️ [V65.14] Guardián de Integridad Judicial.
    Valida la salida de la IA antes de permitir la generación de PDFs oficiales.
    """
    errors = []
    
    # 1. Confianza mínima (Diamond Standard)
    score = legal_json.get("auditoria", {}).get("confidence_score", 0)
    if score < 0.85:
        errors.append(f"Confianza insuficiente ({score:.2f} < 0.85)")
    
    # 2. Campos críticos del Peticionario
    pet = legal_json.get("peticionario", {})
    if not pet.get("nombres") or pet.get("nombres") in ("", "PENDIENTE_VERIFICACION"):
        errors.append("Falta nombre del peticionario verificado")
    if not pet.get("entidad") or pet.get("entidad") == "No especificada":
        # No bloqueamos por entidad si es persona natural, pero avisamos
        logger.warning(f"⚠️ [GUARDIAN] Entidad no especificada para {radicado}")
    
    # 3. Anti-alucinación (Placeholders)
    raw_text = json.dumps(legal_json, ensure_ascii=False).lower()
    found = [ph for ph in PLACEHOLDERS if ph in raw_text]
    if found:
        errors.append(f"Detección de placeholders prohibidos: {found}")
    
    # 4. Validación de Fechas
    fecha_solicitada = original_payload.get("fecha_solicitada")
    if fecha_solicitada:
        try:
            # Si la IA marcó fecha_valida=True pero la fecha es pasada
            fecha_dt = datetime.strptime(fecha_solicitada[:10], "%Y-%m-%d").date()
            if fecha_dt < date.today():
                if legal_json.get("fecha_valida") is not False:
                    errors.append("Discrepancia: Fecha vencida pero IA marcó fecha_valida=True")
        except:
            pass # Formato de fecha no procesable
    
    # 5. Grounding Específico (Salud/Sanitario)
    desc = (str(original_payload.get("descripcion", "")) + " " + str(original_payload.get("asunto", ""))).lower()
    if any(k in desc for k in ["manipulación", "alimento", "salud", "capacitación"]):
        fundamentos = legal_json.get("flujo_documentos", {}).get("proyeccion", {}).get("fundamentos", [])
        # Buscamos Dec 3075 o Res 2674
        has_sanitary = any("3075" in str(f.get("ley","")) or "2674" in str(f.get("ley","")) for f in fundamentos)
        if not has_sanitary:
            errors.append("Falta fundamentación sanitaria obligatoria (Dec 3075/1997 o Res 2674/2013)")
    
    return len(errors) == 0, errors
