from loguru import logger
from typing import Dict, Any

class ScoringService:
    """
    V51.0: Motor de Clasificación de Riesgo y Triaje (Diamond Grade).
    Calcula el nivel de intervención humana requerida.
    """
    
    CRITICAL_KEYWORDS = ["tutela", "muerte", "corrupción", "denuncia", "niño", "niña", "infante", "urgencia vital", "servidor público"]
    
    def calculate_risk(self, extracted_data: dict, motive: str) -> dict:
        """
        Determina el Semáforo de Riesgo: GREEN, YELLOW, RED.
        """
        score = 1.0 # Empezamos en confianza total
        motive_lower = motive.lower()
        
        # 1. Penalización por Palabras Críticas
        found_critical = [kw for kw in self.CRITICAL_KEYWORDS if kw in motive_lower]
        if found_critical:
            score -= (0.2 * len(found_critical))
            logger.warning(f"🚨 Riesgo detectado por keywords: {found_critical}")

        # 2. Penalización por Complejidad de Dependencias
        deps = extracted_data.get("dependencias_involucradas", [])
        if len(deps) > 1:
            score -= 0.15 # Casos intersectoriales requieren más supervisión
            
        # 3. Clasificación Final
        if score < 0.6 or "VITAL" in extracted_data.get("urgencia_flag", ""):
            risk_level = "RED"
        elif score < 0.9:
            risk_level = "YELLOW"
        else:
            risk_level = "GREEN"
            
        logger.info(f"📊 [SCORING] Caso clasificado como {risk_level} (Score: {max(0, score):.2f})")
        
        return {
            "risk_level": risk_level,
            "ai_score": max(0, score),
            "critical_factors": found_critical
        }

scoring_service = ScoringService()
