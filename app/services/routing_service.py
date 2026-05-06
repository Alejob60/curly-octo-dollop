import os
import json
from loguru import logger
from app.core.db_clients import mongo_manager
from app.core.vertex_client import vertex_client
from typing import List, Optional

class DependencyRouter:
    """
    V58.0: Enrutador Jerárquico por Competencia y Riesgo.
    Asegura que el núcleo del problema (ej. derrumbe) gane sobre el contexto (ej. escuela).
    """
    
    PROBLEM_TYPE_PRIORITY = {
        "infraestructura_vial": {
            "keywords": ["derrumbe", "vía", "calzada", "carretera", "puente", "maquinaria", "bache", "deslizamiento", "bacheo", "pavimento"],
            "weight": 10, "dependencies": ["4146"]
        },
        "movilidad_comparendos": {
            "keywords": ["comparendo", "foto-multa", "placa", "simit", "fotomulta", "tránsito", "multa", "vehículo"],
            "weight": 8, "dependencies": ["4152"]
        },
        "salud_urgencia": {
            "keywords": ["hospital", "eps", "medicamentos", "urgencia", "médico", "alimentos", "manipulación", "huv", "vacuna"],
            "weight": 7, "dependencies": ["4135"]
        },
        "educacion": {
            "keywords": ["escuela", "colegio", "estudiante", "docente", "matrícula", "clase", "rector", "cupo"],
            "weight": 3, "dependencies": ["2201"] # Contexto bajo peso
        }
    }

    async def route_case(self, message: str) -> str:
        text = str(message).lower()
        scores = {}

        for p_type, config in self.PROBLEM_TYPE_PRIORITY.items():
            score = 0
            for kw in config["keywords"]:
                if kw in text: score += config["weight"]
            if score > 0:
                scores[p_type] = {"score": score, "dep": config["dependencies"][0]}

        if scores:
            winner = max(scores, key=lambda x: scores[x]["score"])
            logger.info(f"🎯 [ROUTING_HIERARCHICAL] Detectado: {winner} (Score: {scores[winner]['score']})")
            return scores[winner]["dep"]

        # Fallback determinista si no hay pesos
        return "4131"

dependency_router = DependencyRouter()
