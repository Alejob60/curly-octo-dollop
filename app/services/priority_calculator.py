from datetime import datetime, timedelta
import re

def calculate_priority_score(payload: dict) -> dict:
    """
    💎 [V65.14] Scoring de Prioridad Inteligente.
    Urgencia Temporal (40%) + Riesgo Legal (35%) + Complejidad (15%) + Integridad (10%)
    """
    desc = (str(payload.get("descripcion", "")) + " " + str(payload.get("asunto", ""))).lower()
    
    # 1. URGENCIA TEMPORAL (Max 100)
    if any(k in desc for k in ["tutela", "salud", "vida", "menor", "desalojo", "urgente"]):
        days_left, time_score = 3, 100
    elif any(k in desc for k in ["copias", "información", "certificado", "historial"]):
        days_left, time_score = 10, 85
    elif "capacitación" in desc or "evento" in desc:
        days_left, time_score = 15, 70
    else:
        days_left, time_score = 15, 60
    
    # 2. RIESGO LEGAL / COMPLEJIDAD (Max 40)
    risk_keywords = {
        "tutela": 25, "nulidad": 20, "demanda": 20, "comparendo": 15,
        "salud": 15, "vida": 20, "menor": 20, "desalojo": 15,
        "discriminación": 15, "acoso": 15
    }
    risk_score = sum(v for k, v in risk_keywords.items() if k in desc)
    risk_score = min(risk_score, 40)
    
    # 3. DIFICULTAD TÉCNICA (Max 30)
    dep_keywords = ["disponibilidad", "presupuesto", "instructor", "cupo", "espacio", "validar", "coordinar"]
    dep_count = sum(1 for k in dep_keywords if k in desc)
    complexity_score = min(dep_count * 10, 30)
    
    # 4. BONUS: Integridad de datos del peticionario
    pet = payload.get("peticionario") or payload
    completeness_bonus = 10 if all([pet.get("nombres"), pet.get("identificacion"), pet.get("email")]) else 0
    
    # SCORE FINAL (0-100)
    final_score = int((time_score * 0.4) + (risk_score * 0.35) + (complexity_score * 0.15) + completeness_bonus)
    final_score = min(max(final_score, 0), 100)
    
    # NIVEL Y SLA
    if final_score >= 80:
        level, sla_hours = "CRÍTICA", 24
    elif final_score >= 60:
        level, sla_hours = "ALTA", 48
    elif final_score >= 30:
        level, sla_hours = "MEDIA", 72
    else:
        level, sla_hours = "NORMAL", 168
    
    return {
        "score": final_score,
        "level": level,
        "sla_hours": sla_hours,
        "days_left": days_left,
        "components": {
            "time": time_score, "risk": risk_score, 
            "complexity": complexity_score, "completeness": completeness_bonus
        }
    }
