import os, hashlib
from datetime import datetime
from typing import Dict

def prepare_pdf_context(ai_json: dict, metadata: dict, radicado: str) -> dict:
    """
    💎 [V65.12 Diamond] Preparador de Contexto Seguro.
    Transforma la salida de la IA en un contexto listo para Jinja2,
    evitando fallos por datos faltantes o placeholders.
    """
    ctx = {}
    
    # 🆔 Identificación & Datos Ciudadano (Sanitizados)
    ctx["radicado"] = radicado
    ctx["nombre_peticionario"] = (ai_json.get("nombres") or "POR") + " " + (ai_json.get("apellidos") or "VERIFICAR")
    ctx["identificacion"] = ai_json.get("documento") or "POR VERIFICAR"
    
    # Manejar entidad/JAC si existe
    entidad = ai_json.get("entidad") or "No especificada"
    if not entidad or entidad == "No especificada":
        # Intentar extraer de hechos si la IA lo puso ahí
        if "Junta de Acción Comunal" in str(ai_json.get("hechos_extraidos", "")):
            entidad = "Junta de Acción Comunal"
            
    ctx["entidad_solicitante"] = entidad
    ctx["resumen_solicitud"] = ai_json.get("asunto") or "Solicitud administrativa"
    ctx["hechos_extraidos"] = ai_json.get("hechos_extraidos") or ""
    
    # 📅 Fechas & Validación
    now = datetime.now()
    ctx["fecha_generacion"] = now.strftime("%d de %B de %Y %H:%M")
    ctx["fecha_solicitada"] = metadata.get("fecha_solicitada") or "No especificada"
    ctx["fecha_valida"] = metadata.get("fecha_valida", True)
    
    # Alerta de fecha vencida (Requerimiento 2026)
    ctx["alerta_fecha"] = None
    if not ctx["fecha_valida"]:
        ctx["alerta_fecha"] = "⚠️ La fecha solicitada ya transcurrió. Conforme al Art. 14 de la Ley 1755 de 2015, se requiere reprogramación inmediata."
        
    # ⚖️ Normativa & Plazos
    ctx["citas_verificables"] = ai_json.get("citas_verificables") or []
    ctx["borrador_proyeccion"] = ai_json.get("borrador_proyeccion") or "En trámite..."
    ctx["plazo_dias"] = ai_json.get("plazo_dias", 15)
    ctx["canal_notificacion"] = ai_json.get("canal_notificacion", "electrónico y físico")
    ctx["entidad_destino"] = metadata.get("entidad_destino") or "SECRETARÍA COMPETENTE"
    
    # Datos de contacto
    ctx["email"] = ai_json.get("email") or "No disponible"
    ctx["celular"] = ai_json.get("celular") or "No disponible"
    ctx["direccion"] = ai_json.get("direccion") or "No disponible"

    # 🏢 Logística & Programación
    ctx["instructor_asignado"] = ai_json.get("instructor") or "Por confirmar por Dirección Técnica"
    ctx["cupos_solicitados"] = ai_json.get("cupos") or "A definir por entidad territorial"
    ctx["lugar_programado"] = ai_json.get("lugar") or "Sede comunal o auditorio municipal asignado"

    # 🛡️ Metadata de Sistema
    ctx["version_engine"] = os.getenv("APP_VERSION", "V65.12")
    ctx["hash_documento"] = hashlib.sha256(f"{radicado}-{now.isoformat()}".encode()).hexdigest()[:16]
    ctx["titulo_documento"] = "" # Se sobreescribe por template
    
    return ctx
