from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import re
from loguru import logger

class ProblemPriority(Enum):
    CRITICAL = 5  # Riesgo físico inminente, urgencia vital
    HIGH = 4      # Comparendos, infraestructura dañada
    MEDIUM = 3    # Capacitaciones, trámites administrativos
    LOW = 2       # Consultas, contexto secundario
    CONTEXT = 1   # Palabras de ubicación/entorno, no problema principal

@dataclass
class SemanticToken:
    keyword: str
    priority: ProblemPriority
    category: str  # "infraestructura", "salud", "movilidad", "educacion", "contexto"
    weight: float = 1.0

@dataclass
class ContextAnalysis:
    primary_problem: str
    problem_type: str
    context_elements: List[str]
    urgency_level: str
    confidence_score: float
    matched_tokens: List[SemanticToken]
    suggested_dependencies: List[str]

class HermesContextEngine:
    """
    Motor de análisis de contexto con prioridad semántica jerárquica.
    Distingue entre problema principal y contexto secundario.
    """
    
    SEMANTIC_TOKENS = {
        # Infraestructura vial (PRIORIDAD ALTA)
        "derrumbe": SemanticToken("derrumbe", ProblemPriority.CRITICAL, "infraestructura", weight=2.0),
        "vía": SemanticToken("vía", ProblemPriority.HIGH, "infraestructura"),
        "calzada": SemanticToken("calzada", ProblemPriority.HIGH, "infraestructura"),
        "carretera": SemanticToken("carretera", ProblemPriority.HIGH, "infraestructura"),
        "puente": SemanticToken("puente", ProblemPriority.HIGH, "infraestructura"),
        "maquinaria": SemanticToken("maquinaria", ProblemPriority.HIGH, "infraestructura"),
        "señalización": SemanticToken("señalización", ProblemPriority.MEDIUM, "infraestructura"),
        "bache": SemanticToken("bache", ProblemPriority.MEDIUM, "infraestructura"),
        "bacheo": SemanticToken("bacheo", ProblemPriority.MEDIUM, "infraestructura"),
        "pavimento": SemanticToken("pavimento", ProblemPriority.MEDIUM, "infraestructura"),
        "obstrucción": SemanticToken("obstrucción", ProblemPriority.HIGH, "infraestructura"),
        
        # Salud urgente (PRIORIDAD CRÍTICA)
        "hospital": SemanticToken("hospital", ProblemPriority.CRITICAL, "salud"),
        "eps": SemanticToken("eps", ProblemPriority.HIGH, "salud"),
        "soat": SemanticToken("soat", ProblemPriority.HIGH, "salud"),
        "medicamentos": SemanticToken("medicamentos", ProblemPriority.CRITICAL, "salud"),
        "urgencia": SemanticToken("urgencia", ProblemPriority.CRITICAL, "salud"),
        "médico": SemanticToken("médico", ProblemPriority.CRITICAL, "salud"),
        "alimentos": SemanticToken("alimentos", ProblemPriority.MEDIUM, "salud"),
        "manipulación": SemanticToken("manipulación", ProblemPriority.MEDIUM, "salud"),
        "sanitario": SemanticToken("sanitario", ProblemPriority.HIGH, "salud"),
        "salud": SemanticToken("salud", ProblemPriority.MEDIUM, "salud"),
        
        # Trámites/Capacitaciones (PRIORIDAD MEDIA)
        "capacitación": SemanticToken("capacitación", ProblemPriority.MEDIUM, "contexto"),
        "jornada": SemanticToken("jornada", ProblemPriority.LOW, "contexto"),
        "taller": SemanticToken("taller", ProblemPriority.LOW, "contexto"),
        "curso": SemanticToken("curso", ProblemPriority.LOW, "contexto"),
        "certificado": SemanticToken("certificado", ProblemPriority.MEDIUM, "contexto"),
        
        # Movilidad/comparendos (PRIORIDAD MEDIA-ALTA)
        "comparendo": SemanticToken("comparendo", ProblemPriority.HIGH, "movilidad"),
        "foto-multa": SemanticToken("foto-multa", ProblemPriority.HIGH, "movilidad"),
        "fotomulta": SemanticToken("fotomulta", ProblemPriority.HIGH, "movilidad"),
        "placa": SemanticToken("placa", ProblemPriority.MEDIUM, "movilidad"),
        "tránsito": SemanticToken("tránsito", ProblemPriority.MEDIUM, "movilidad"),
        "multa": SemanticToken("multa", ProblemPriority.MEDIUM, "movilidad"),
        
        # Educación (PRIORIDAD BAJA - usualmente contexto)
        "escuela": SemanticToken("escuela", ProblemPriority.LOW, "educacion", weight=0.5),
        "colegio": SemanticToken("colegio", ProblemPriority.LOW, "educacion", weight=0.5),
        "estudiante": SemanticToken("estudiante", ProblemPriority.CONTEXT, "educacion"),
        "docente": SemanticToken("docente", ProblemPriority.CONTEXT, "educacion"),
        
        # Contexto/ubicación
        "vereda": SemanticToken("vereda", ProblemPriority.CONTEXT, "contexto"),
        "barrio": SemanticToken("barrio", ProblemPriority.CONTEXT, "contexto"),
        "cerca de": SemanticToken("cerca de", ProblemPriority.CONTEXT, "contexto"),
        "junto a": SemanticToken("junto a", ProblemPriority.CONTEXT, "contexto"),
    }
    
    PROBLEM_TO_DEPENDENCIES = {
        "infraestructura": ["4146"], 
        "salud": ["4135"],
        "movilidad": ["4152"],
        "educacion": ["2201"],
        "contexto": ["4131"]
    }
    
    async def analyze(self, text: str) -> ContextAnalysis:
        t = text.lower()
        matched_tokens = []
        category_scores = {}
        
        for kw, token in self.SEMANTIC_TOKENS.items():
            if kw in t:
                matched_tokens.append(token)
                category = token.category
                category_scores[category] = category_scores.get(category, 0) + (token.priority.value * token.weight)
        
        valid_categories = {k: v for k, v in category_scores.items() if k != "contexto"}
        
        if not valid_categories:
            return ContextAnalysis("General", "contexto", [], "NORMAL", 0.5, matched_tokens, ["4131"])
        
        primary_category = max(valid_categories, key=valid_categories.get)
        primary_score = valid_categories[primary_category]
        
        context_elements = [t.keyword for t in matched_tokens if t.priority == ProblemPriority.CONTEXT]
        has_critical = any(t.priority == ProblemPriority.CRITICAL for t in matched_tokens)
        urgency = "CRÍTICA" if has_critical else "ALTA" if primary_score >= 10 else "NORMAL"
        
        confidence = min(1.0, len(matched_tokens) * 0.15 + (0.2 if has_critical else 0))
        suggested_deps = self.PROBLEM_TO_DEPENDENCIES.get(primary_category, ["4131"])
        
        return ContextAnalysis(
            primary_problem=primary_category.replace('_', ' ').title(),
            problem_type=primary_category,
            context_elements=context_elements,
            urgency_level=urgency,
            confidence_score=confidence,
            matched_tokens=matched_tokens,
            suggested_dependencies=suggested_deps
        )

hermes_context = HermesContextEngine()
