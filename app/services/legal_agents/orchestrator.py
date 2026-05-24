from app.services.legal_agents.state import LegalCaseState
from app.services.legal_agents.extractor import FactExtractorAgent
from app.services.legal_agents.researcher import LegalResearcherAgent
from app.services.legal_agents.crafter import DocumentCrafterAgent
from app.services.legal_agents.reviewer import ComplianceReviewerAgent
from app.services.legal_agents.calilex import CalilexAgent
from app.services.persistence_bridge import persistence_bridge
from loguru import logger
import asyncio
import json

class LegalOrchestrator:
    """
    Cerebro Multiagente V1.0 - Integración Cali-Lex Advisor V65.6.
    Coordina agentes especializados para el escalado legal de Orbital Prime.
    """
    def __init__(self):
        self.agents = {
            "extractor": FactExtractorAgent(),
            "researcher": LegalResearcherAgent(),
            "crafter": DocumentCrafterAgent(),
            "reviewer": ComplianceReviewerAgent(),
            "calilex": CalilexAgent()  # ⚖️ Nuevo agente de auditoría forense
        }
    
    async def process(self, session_id: str, raw_input: str, case_type: str = "pqrs", extra_prompt: str = None) -> LegalCaseState:
        logger.info(f"🧠 [LEGAL_ORCHESTRATOR] Iniciando proceso para {case_type} | Session: {session_id}")
        state = LegalCaseState(session_id=session_id, raw_input=raw_input, case_type=case_type)
        
        # FASE 1 & 2: Extracción y RAG
        for agent_name in ["extractor", "researcher"]:
            agent = self.agents[agent_name]
            if await agent.validate_input(state):
                try:
                    logger.info(f"🛰️ [PHASE_PRE_{agent_name.upper()}] Ejecutando...")
                    output = await agent.execute(state)
                    logger.info(f"📥 [AGENT_{agent_name.upper()}_JSON_RESPONSE]: {json.dumps(output, indent=2, ensure_ascii=False)}")
                    state = self._update_state(state, agent_name, output)
                except Exception as e:
                    logger.error(f"❌ Error en AGENTE_{agent_name.upper()}: {e}")

        # FASE 3 & 4: Ciclo de Creación y Auditoría Recursiva (FIX V64.2)
        max_retries = 2
        attempt = 0
        quality_threshold = 0.8
        
        while attempt <= max_retries:
            attempt += 1
            logger.info(f"🤖 [CRAFTER_LOOP] Intento {attempt} para {session_id}")
            
            # 1. Generar Borrador
            crafter = self.agents["crafter"]
            feedback = None
            if attempt > 1:
                feedback = f"AUDITORÍA PREVIA FALLIDA (Score: {state.review_score}). " \
                           f"NOTAS: {'. '.join(state.review_notes[-3:])}. " \
                           f"FALTANTE: {'. '.join(getattr(state, 'missing_elements', []))}"
            
            try:
                logger.info(f"🛠️ [PHASE_PRE_CRAFTER] Generando borrador (Intento {attempt})...")
                craft_output = await crafter.execute(state, extra_prompt=feedback)
                logger.info(f"📥 [AGENT_CRAFTER_JSON_RESPONSE]: {json.dumps(craft_output, indent=2, ensure_ascii=False)}")
                state = self._update_state(state, "crafter", craft_output)
            except Exception as e:
                logger.error(f"❌ Error en CRAFTER: {e}")
                break

            # --- 🔍 AUDITORÍA: ANTES DE PASAR AL REVIEWER ---
            pre_audit_json = {
                "nombres": state.nombres, "apellidos": state.apellidos,
                "hechos": state.facts, "borrador": state.draft_document[:500] + "...",
                "citas": state.legal_basis
            }
            logger.info(f"📝 [BEFORE_AUDIT_JSON]: {json.dumps(pre_audit_json, indent=2, ensure_ascii=False)}")

            # 2. Auditar Borrador
            reviewer = self.agents["reviewer"]
            try:
                logger.info(f"⚖️ [PHASE_PRE_REVIEWER] Iniciando auditoría legal...")
                review_output = await reviewer.execute(state)
                logger.info(f"📥 [AGENT_REVIEWER_JSON_RESPONSE]: {json.dumps(review_output, indent=2, ensure_ascii=False)}")
                state = self._update_state(state, "reviewer", review_output)
                state.missing_elements = review_output.get("missing", [])
            except Exception as e:
                logger.error(f"❌ Error en REVIEWER: {e}")
                break

            # --- 🔍 AUDITORÍA: DESPUÉS DE PASAR POR EL REVIEWER ---
            post_audit_summary = {
                "status": state.review_status,
                "score": state.review_score,
                "notes": state.review_notes[-2:],
                "missing": getattr(state, 'missing_elements', [])
            }
            logger.info(f"🏁 [AFTER_AUDIT_JSON_SUMMARY]: {json.dumps(post_audit_summary, indent=2, ensure_ascii=False)}")

            # 3. Verificar Umbral de Calidad
            if state.review_score >= quality_threshold:
                logger.success(f"✅ [ORCHESTRATOR] Calidad certificada: {state.review_score} [Attempt: {attempt}]")
                break
            else:
                logger.warning(f"⚠️ [ORCHESTRATOR] Calidad insuficiente ({state.review_score}). Re-generando con feedback...")

        # FASE 5: Auditoría Forense Cali-Lex Advisor V65.6 (POST-PROCESAMIENTO)
        logger.info("⚖️ [CALILEX_PHASE] Iniciando auditoría forense post-procesamiento...")
        try:
            calilex_agent = self.agents["calilex"]
            calilex_audit = await calilex_agent.analyze_case_quality(state)
            
            # Inyectar resultados de Calilex en el estado
            state.confidence_score = calilex_audit.get("confidence_score", 0.0)
            state.grounding_score = calilex_audit.get("grounding_score", 0.0)
            state.completeness_score = calilex_audit.get("completeness_score", 0.0)
            state.complexity_level = calilex_audit.get("complexity_level", "MEDIUM")
            state.integrity_hash = calilex_audit.get("integrity_hash", "")
            state.calilex_version = calilex_audit.get("version_engine", "V65.6")
            state.pdf_blocked = calilex_audit.get("pdf_blocked", False)
            state.calilex_block_reason = calilex_audit.get("block_reason")
            state.fecha_alert = calilex_audit.get("fecha_alert")
            state.human_review_required = calilex_audit.get("human_review_required", False)
            
            logger.info(f"✅ [CALILEX_AUDIT_COMPLETE] Confidence: {state.confidence_score:.3f} | Blocked: {state.pdf_blocked}")
        except Exception as e:
            logger.error(f"❌ [CALILEX_PHASE_ERROR] {e}")
            # No bloquear el flujo, pero marcar para revisión humana
            state.human_review_required = True

        # Sincronizar con el puente de persistencia
        await self._persist_state(state)
        return state
    
    def _update_state(self, state: LegalCaseState, agent_name: str, output: dict) -> LegalCaseState:
        state.add_step(agent_name, output)
        if "facts" in output: state.facts = output["facts"]
        if "nombres" in output: state.nombres = output["nombres"]
        if "apellidos" in output: state.apellidos = output["apellidos"]
        if "documento" in output: state.documento = output["documento"]
        if "email" in output: state.email = output["email"]
        if "celular" in output: state.celular = output["celular"]
        if "direccion" in output: state.direccion = output["direccion"]
        if "legal_basis" in output: state.legal_basis = output["legal_basis"]
        if "citations_block" in output: state.citations_block = output["citations_block"]
        if "draft" in output: state.draft_document = output["draft"]
        if "package" in output: state.document_package = output["package"]
        if "review_status" in output: state.review_status = output["review_status"]
        if "score" in output: state.review_score = output["score"]
        if "notes" in output: state.review_notes.extend(output["notes"])
        return state
    
    async def _persist_state(self, state: LegalCaseState):
        radicado = f"LEGAL-{state.session_id[-4:].upper()}"
        
        # Preparar datos para persistencia incluyendo métricas Calilex
        persistence_data = {
            "tipo_solicitud": state.case_type.upper(),
            "estado": "REVISADO" if state.review_status == "approved" else "BORRADOR",
            "hechos_extraidos": "\n".join(state.facts),
            "borrador_proyeccion": state.draft_document,
            "review_score": getattr(state, "review_score", 0.5),
            # Métricas Calilex V65.6 para analítica PQRS
            "confidence_score": getattr(state, "confidence_score", 0.0),
            "grounding_score": getattr(state, "grounding_score", 0.0),
            "completeness_score": getattr(state, "completeness_score", 0.0),
            "complexity_level": getattr(state, "complexity_level", "MEDIUM"),
            "integrity_hash": getattr(state, "integrity_hash", ""),
            "calilex_version": getattr(state, "calilex_version", "V65.6"),
            "pdf_blocked": getattr(state, "pdf_blocked", False),
            "human_review_required": getattr(state, "human_review_required", False)
        }
        
        await persistence_bridge.save_progress(state.session_id, radicado, persistence_data)

legal_orchestrator = LegalOrchestrator()
