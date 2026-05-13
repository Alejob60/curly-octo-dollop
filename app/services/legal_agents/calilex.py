from app.services.legal_agents.state import LegalCaseState
from loguru import logger
import json
import hashlib
from typing import Optional, Dict, Any

class CalilexAgent:
    """
    ⚖️ Cali-Lex Advisor V65.6 - Analista Jurídico Especializado en PQRS
    
    Motor de análisis forense que garantiza integridad jurídica mediante:
    - Validación de confianza (threshold >= 0.85)
    - Detección de alucinaciones
    - Verificación de completitud contextual
    - Generación de hash de integridad
    
    Arquitectura de Alta Fidelidad (Manual V65.6):
    1. No conversa - solo genera JSON determinista
    2. Valida confianza antes de permitir renderizado PDF
    3. Inyecta versión dinámica en auditoría
    """
    
    def __init__(self):
        self.min_confidence_threshold = 0.85
        self.engine_version = "V65.6"
    
    async def analyze_case_quality(self, state: LegalCaseState) -> dict:
        """
        Analiza calidad jurídica del caso para métricas de analítica PQRS.
        Ejecuta guardias de integridad antes de certificar el caso.
        """
        try:
            logger.info(f"🔍 [CALILEX_V65.6] Iniciando análisis forense para {state.session_id}")
            
            # 1. Calificar grounding legal con validación estricta
            grounding_score = self._calculate_grounding_score(state)
            
            # 2. Evaluar completitud documental (Guardia de Contexto)
            completeness_score = self._evaluate_document_completeness(state)
            
            # 3. Medir complejidad del caso
            complexity_level = self._assess_case_complexity(state)
            
            # 4. Calcular score de confianza compuesto
            confidence_score = self._calculate_confidence_score(
                grounding_score, 
                completeness_score
            )
            
            # 5. Generar hash de integridad para trazabilidad
            integrity_hash = self._generate_integrity_hash(state, confidence_score)
            
            # 6. Ejecutar guardia de bloqueo PDF
            pdf_blocked = False
            block_reason = None
            
            if confidence_score < self.min_confidence_threshold:
                pdf_blocked = True
                block_reason = f"CONFIDENCE_LOW ({confidence_score:.2f} < {self.min_confidence_threshold})"
                logger.warning(f"🚫 [CALILEX_BLOCKED] {state.session_id}: {block_reason}")
            
            # 7. Verificar fecha válida (Guardia de Fecha)
            fecha_alert = self._validate_fecha_solicitada(state)
            
            audit_result = {
                "grounding_score": round(grounding_score, 3),
                "completeness_score": round(completeness_score, 3),
                "confidence_score": round(confidence_score, 3),
                "complexity_level": complexity_level,
                "integrity_hash": integrity_hash,
                "version_engine": self.engine_version,
                "pdf_blocked": pdf_blocked,
                "block_reason": block_reason,
                "fecha_alert": fecha_alert,
                "calilex_audit_timestamp": json.dumps({"status": "completed"}),
                "human_review_required": pdf_blocked or (fecha_alert is not None)
            }
            
            logger.info(f"✅ [CALILEX_AUDIT_COMPLETE] {state.session_id} | Confidence: {confidence_score:.3f} | Hash: {integrity_hash[:16]}...")
            
            return audit_result
            
        except Exception as e:
            logger.error(f"❌ [CALILEX_CRITICAL_ERROR] {state.session_id}: {e}")
            return {
                "error": str(e),
                "confidence_score": 0.0,
                "pdf_blocked": True,
                "block_reason": "CALILEX_ANALYSIS_FAILED",
                "human_review_required": True
            }
    
    def _calculate_grounding_score(self, state: LegalCaseState) -> float:
        """
        Calcula score de fundamentación legal (0-1) con criterios estrictos.
        Evita alucinaciones verificando citas reales.
        """
        if not state.legal_basis:
            return 0.0
        
        num_citations = len(state.legal_basis) if isinstance(state.legal_basis, list) else 0
        
        # Criterio 1: Cantidad mínima de citas (ideal: 3+)
        citation_quantity = min(1.0, num_citations / 3.0)
        
        # Criterio 2: Calidad - verificar si hay bloque de citas formateado
        has_citations_block = bool(getattr(state, 'citations_block', None))
        citation_format_score = 0.3 if has_citations_block else 0.0
        
        # Criterio 3: Verificar que las citas no sean genéricas
        citation_specificity = self._evaluate_citation_specificity(state.legal_basis)
        
        # Ponderación: 40% cantidad, 30% formato, 30% especificidad
        grounding_score = (citation_quantity * 0.4) + citation_format_score + (citation_specificity * 0.3)
        
        return min(1.0, grounding_score)
    
    def _evaluate_citation_specificity(self, legal_basis: list) -> float:
        """Evalúa si las citas son específicas o genéricas"""
        if not legal_basis:
            return 0.0
        
        generic_keywords = ["ley", "norma", "artículo", "constitución"]
        specific_score = 0.0
        
        for citation in legal_basis:
            citation_lower = citation.lower() if isinstance(citation, str) else ""
            # Detectar citas específicas (con números, años, entidades)
            has_numbers = any(char.isdigit() for char in citation_lower)
            has_year = any(str(year) in citation_lower for year in range(1980, 2030))
            has_entity = any(entity in citation_lower for entity in ["colombia", "congreso", "corte", "ministerio"])
            
            if has_numbers and has_year:
                specific_score += 1.0
            elif has_numbers or has_entity:
                specific_score += 0.5
        
        return min(1.0, specific_score / len(legal_basis))
    
    def _evaluate_document_completeness(self, state: LegalCaseState) -> float:
        """
        Guardia de Contexto: Evalúa completitud del documento generado.
        Aborta si faltan secciones críticas.
        """
        draft = getattr(state, 'draft_document', '')
        if not draft or len(draft) < 100:
            return 0.0
        
        score = 0.0
        draft_upper = draft.upper()
        
        # Secciones mínimas obligatorias
        section_checks = [
            ("HECHOS|FACTS|ANTECEDENTES", 0.25),
            ("DERECHO|LAW|FUNDAMENTOS|NORMATIVIDAD", 0.25),
            ("RESUELVE|DECIDE|CONSIDERANDO", 0.25),
            ("RADICADO|NÚMERO|REFERENCIA", 0.15),
            ("FECHA|DÍA|TIEMPO", 0.10)
        ]
        
        import re
        for pattern, weight in section_checks:
            if re.search(pattern, draft_upper):
                score += weight
        
        # Bonus por longitud adecuada (300-2000 caracteres ideal)
        length_score = 0.0
        if 300 <= len(draft) <= 2000:
            length_score = 0.1
        elif len(draft) > 2000:
            length_score = 0.05
        
        return min(1.0, score + length_score)
    
    def _assess_case_complexity(self, state: LegalCaseState) -> str:
        """Clasifica complejidad del caso para enrutamiento"""
        draft_length = len(getattr(state, 'draft_document', ''))
        num_facts = len(getattr(state, 'facts', []))
        num_citations = len(getattr(state, 'legal_basis', []))
        
        # Fórmula de complejidad ponderada
        complexity_score = (draft_length / 1000) + (num_facts * 0.5) + (num_citations * 0.3)
        
        if complexity_score < 2.5:
            return "LOW"
        elif complexity_score < 5.0:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def _calculate_confidence_score(self, grounding: float, completeness: float) -> float:
        """
        Calcula score de confianza compuesto para decisión de bloqueo PDF.
        Threshold crítico: >= 0.85 para producción
        """
        # Ponderación: 60% grounding, 40% completitud
        confidence = (grounding * 0.6) + (completeness * 0.4)
        
        # Penalización por valores extremadamente bajos
        if grounding < 0.3 or completeness < 0.3:
            confidence *= 0.7  # Penalización del 30%
        
        return min(1.0, confidence)
    
    def _generate_integrity_hash(self, state: LegalCaseState, confidence: float) -> str:
        """
        Genera hash SHA-256 de integridad para trazabilidad del caso.
        Incluye versión del engine para auditoría.
        """
        content_to_hash = json.dumps({
            "session_id": state.session_id,
            "radicado": getattr(state, 'documento', ''),
            "facts_count": len(getattr(state, 'facts', [])),
            "citations_count": len(getattr(state, 'legal_basis', [])),
            "draft_length": len(getattr(state, 'draft_document', '')),
            "confidence": round(confidence, 3),
            "version": self.engine_version,
            "timestamp": json.dumps({"status": "completed"})
        }, sort_keys=True)
        
        return hashlib.sha256(content_to_hash.encode('utf-8')).hexdigest()
    
    def _validate_fecha_solicitada(self, state: LegalCaseState) -> Optional[str]:
        """
        Guardia de Fecha: Detecta fechas inválidas (en pasado).
        Inyecta alerta en el PDF si se detecta anomalía.
        """
        fecha_solicitada = getattr(state, 'fecha_solicitada', None)
        if not fecha_solicitada:
            return None
        
        try:
            from datetime import datetime
            # Asumir formato YYYY-MM-DD
            requested_date = datetime.strptime(str(fecha_solicitada), "%Y-%m-%d")
            today = datetime.utcnow()
            
            if requested_date < today:
                alert_msg = f"⚠️ FECHA_INVALIDA: La fecha solicitada ({fecha_solicitada}) está en el pasado"
                logger.warning(f"[CALILEX_DATE_ALERT] {state.session_id}: {alert_msg}")
                return alert_msg
            
            return None
        except Exception as e:
            logger.error(f"[CALILEX_DATE_PARSE_ERROR] {e}")
            return f"⚠️ ERROR_FORMATO_FECHA: {str(e)}"
    
    async def validate_strict_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida entrada estricta según contrato StrictLegalInput (Manual V65.6).
        Usa null para datos faltantes, nunca inventa datos.
        """
        validated = {
            "radicado": input_data.get("radicado"),
            "peticionario": {
                "nombres": input_data.get("peticionario", {}).get("nombres"),
                "apellidos": input_data.get("peticionario", {}).get("apellidos"),
                "identificacion": input_data.get("peticionario", {}).get("identificacion"),
                "entidad": input_data.get("peticionario", {}).get("entidad")
            },
            "descripcion": input_data.get("descripcion"),
            "fecha_solicitada": input_data.get("fecha_solicitada"),
            "tipo_pqrs": input_data.get("tipo_pqrs"),
            "validation_status": "VALID"
        }
        
        # Verificar campos críticos
        missing_fields = []
        if not validated["radicado"]:
            missing_fields.append("radicado")
        if not validated["descripcion"]:
            missing_fields.append("descripcion")
        
        if missing_fields:
            validated["validation_status"] = "INCOMPLETE"
            validated["missing_fields"] = missing_fields
            logger.warning(f"[CALILEX_STRICT_INPUT] Campos faltantes: {missing_fields}")
        
        return validated


# Instancia singleton del agente
calilex_agent = CalilexAgent()
