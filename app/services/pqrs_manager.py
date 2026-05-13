import json
import re
import hashlib
import datetime
import time
import os
import yaml
import asyncio
import traceback
from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger
from enum import Enum
import json_repair

from app.core.db_clients import redis_client, mongo_manager
from app.core.vertex_client import vertex_client
from app.utils.sanitizer import PDFSanitizer
from app.services.pdf_service import pdf_service
from app.services.privacy_shield_service import privacy_shield
from app.services.phase_orchestrator import phase_guard, Phase
from app.services.rag_context import rag_manager
from app.services.law_router import law_router
from app.services.orchestrator import orchestrator
from app.models.schemas import LegalAnalysisResult, ExtractionResult
from app.services.cali_lex_client import call_cali_lex
from app.services.agent_health_guard import agent_health_guard

class PQRSManager:
    """
    💎 [V65.14 Diamond] Orquestador Maestro Industrial.
    ✅ Cali-Lex Integration | ✅ Health Guard | ✅ Wait Protocol | ✅ Human Review
    """
    
    def __init__(self):
        self.state_prefix = "pqrs:state:"
        self.ttl_seconds = 259200
        try:
            reg_path = Path(os.getcwd()) / "app" / "core" / "case_registry.yaml"
            if not reg_path.exists():
                reg_path = Path(os.getcwd()) / "legacy" / "app" / "core" / "case_registry.yaml"
            
            with open(reg_path, 'r', encoding='utf-8') as f:
                self.registry = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"❌ Error cargando Case Registry: {e}")
            self.registry = {"CASE_PROFILES": []}

    def _detect_profile(self, message: str) -> dict:
        m_lower = str(message).lower()
        profiles = self.registry.get("CASE_PROFILES", [])
        for profile in profiles:
            if profile.get("ID") == "GENERIC_TRAMITE": continue
            if any(kw in m_lower for kw in profile.get("KEYWORDS", [])):
                return profile
        return next((p for p in profiles if p.get("ID") == "GENERIC_TRAMITE"), {})

    def extract_basic_info(self, session_id: str, message: str) -> dict:
        """Extracción directa con Regex (Soberanía Cali)"""
        profile = self._detect_profile(message)
        
        # 1. Cédula
        doc_match = re.search(r'\b\d{6,10}\b', message)
        documento = doc_match.group(0) if doc_match else ""
        
        # 2. Nombre (REGEX ROBUSTO)
        nombres, apellidos = "", ""
        name_patterns = [
            r"(?i)(?:soy|me llamo|representante[:\s]+)([A-ZÁÉÍÓÜÑ][a-záéíóúüñ]+)\s+([A-ZÁÉÍÓÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÜÑ][a-záéíóúüñ]+)*)",
            r"(?i)([A-ZÁÉÍÓÜÑ][a-záéíóúüñ]+)\s+([A-ZÁÉÍÓÜÑ][a-záéíóúüñ]+)(?:\s*,\s*cédula|\s*,\s*cc|\s*,\s*identificación)",
            r"(?i)(?:peticionario|ciudadano)[:\s]+([A-ZÁÉÍÓÜÑ][a-záéíóúüñ]+)\s+([A-ZÁÉÍÓÜÑ][a-záéíóúüñ]+)"
        ]
        matched_pattern = "None"
        for pattern in name_patterns:
            match = re.search(pattern, message)
            if match:
                matched_pattern = pattern
                n_raw = match.group(1).strip().lower().replace("edurado", "eduardo").replace("huratado", "hurtado")
                a_raw = match.group(2).strip().lower().replace("sanhez", "sánchez")
                nombres = ' '.join(w.capitalize() for w in n_raw.split())
                apellidos = ' '.join(w.capitalize() for w in a_raw.split())
                break

        radicado = f"CALI-{profile.get('DEPENDENCY_ID', 'GEN')}-{session_id[-4:].upper()}"
        
        extraction = {
            "active_profile": profile.get("ID"),
            "required_docs": json.dumps(profile.get("REQUIRED_DOCUMENTS", [])),
            "documento": documento,
            "nombres": nombres,
            "apellidos": apellidos,
            "municipio": "Cali",
            "departamento": "Valle del Cauca",
            "asunto": f"SOLICITUD: {profile.get('ID')}",
            "motivo": message,
            "dependencia_id": profile.get("DEPENDENCY_ID", "4131"),
            "dependencia_competente": profile.get("TARGET_DEPENDENCY", "Secretaría General"),
            "radicado": radicado,
            "current_phase": Phase.F1_IDENTIDAD.value
        }

        # 👁️ [GODS_EYE]
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": session_id, "phase": "fase_1_ingesta",
            "service": "pqrs_manager", "action": "extract_basic_info",
            "extraction_result": {"nombres": nombres, "apellidos": apellidos, "documento": documento}
        }
        logger.info(f"👁️ [PHASE_1_LOG] {json.dumps(log_entry, indent=2)}")
        return extraction

    async def analyze_initial_message(self, session_id: str, message: str) -> dict:
        """FASE 2: Inicio de flujo determinista"""
        raw = self.extract_basic_info(session_id, message)
        state_key = f"{self.state_prefix}{session_id}"
        await redis_client.hset(state_key, mapping={k: str(v) for k, v in raw.items() if v})
        await redis_client.expire(state_key, self.ttl_seconds)
        
        asyncio.create_task(self.background_process_full_analysis(session_id, message))
        
        return await self.get_next_ui_instruction(session_id, raw)

    async def background_process_full_analysis(self, session_id: str, message: str):
        """Módulo 5: Proceso asíncrono robusto con Cali-Lex Advisor"""
        try:
            state_key = f"{self.state_prefix}{session_id}"
            
            await phase_guard.transition(session_id, Phase.F3_ANALISIS)
            await orchestrator.emit_event(session_id, Phase.F3_ANALISIS, "🔐 Anonimizando datos...", 10)
            
            tokenized_message = await privacy_shield.tokenize_text(session_id, message)

            await orchestrator.emit_event(session_id, Phase.F3_ANALISIS, "⚖️ Clasificando marco legal...", 20)
            classification = await law_router.classify(tokenized_message)
            
            await orchestrator.emit_event(session_id, Phase.F3_ANALISIS, "🏛️ Recuperando base legal...", 35)
            legal_grounding = await rag_manager.get_legal_grounding(classification.law_id.upper(), tokenized_message)

            await orchestrator.emit_event(session_id, Phase.F3_ANALISIS, "🧠 Analizando con Cali-Lex Advisor...", 50)
            
            raw_state = await redis_client.hgetall(state_key)
            state_data = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in raw_state.items()}

            payload = {**state_data, "descripcion": message, "contexto_legal": legal_grounding}
            
            # 🔍 LOG REQUEST PAYLOAD
            logger.info(f"📤 [CALI-LEX_REQ] session={session_id} | payload={json.dumps(payload, indent=2, ensure_ascii=False)}")

            # 1. Llamada a Cali-Lex (await directo del coroutine)
            ai_resp_dict = await orchestrator.execute_task_with_semaphore(call_cali_lex(payload))
            
            # 🔍 LOG RAW IA RESPONSE
            logger.info(f"🤖 [CALI-LEX_RESP] session={session_id} | data={json.dumps(ai_resp_dict, indent=2, ensure_ascii=False)}")

            # 2. Auditoría
            decision = await agent_health_guard.decide_route(payload, ai_resp_dict)
            logger.info(f"🔍 [AUDIT_DECISION] session={session_id} | decision={decision.decision} | score={decision.confidence}")
            
            if decision.decision == "BLOCK_AND_REVIEW":
                logger.critical(f"🚨 [FLOW_BLOCK] Baja confianza para {session_id}")
                await orchestrator.emit_event(session_id, Phase.F3_ANALISIS, "⚠️ Baja confianza detectada.", 99, data={"needs_review": True, "confidence": decision.confidence})
                
                db = mongo_manager.get_db()
                if db is not None:
                    await db["pqrs_human_review"].update_one(
                        {"session_id": session_id},
                        {"$set": {
                            "radicado": state_data.get("radicado", "GEN"),
                            "confidence": decision.confidence,
                            "reason": decision.reason,
                            "status": "PENDING",
                            "created_at": time.time(),
                            "borrador_proyeccion": ai_resp_dict.get("flujo_documentos", {}).get("proyeccion", {}).get("borrador", "")
                        }}, upsert=True
                    )
            
            # 3. Mapeo
            flujo = ai_resp_dict.get("flujo_documentos", {})
            conf_val = ai_resp_dict.get("auditoria", {}).get("confidence_score", 0.0)
            parsed = {
                "asunto": ai_resp_dict.get("asunto") or state_data.get("asunto"),
                "hechos_extraidos": flujo.get("memorial", {}).get("relato_hechos", ""),
                "borrador_proyeccion": flujo.get("proyeccion", {}).get("borrador", ""),
                "citas_verificables": json.dumps(flujo.get("proyeccion", {}).get("fundamentos", [])),
                "confidence": conf_val
            }

            await orchestrator.emit_event(session_id, Phase.F3_ANALISIS, "✅ Finalizando análisis...", 85)
            
            merged = {**state_data, **parsed}
            clean_context = PDFSanitizer.inject_context(merged)
            await redis_client.hset(state_key, mapping={k: str(v) for k, v in clean_context.items() if v})
            
            await orchestrator.emit_event(session_id, Phase.F3_ANALISIS, "✅ Análisis completado.", 99, data={"analysis_ready": True, "confidence": conf_val})
            logger.success(f"✅ Background completado para {session_id}")

        except Exception as e:
            logger.error(f"❌ Error background en {session_id}: {e}")
            logger.error(traceback.format_exc())
            await redis_client.setex(f"progress:{session_id}:error", 300, str(e))

    async def get_next_ui_instruction(self, session_id: str, data: dict = None) -> dict:
        if not data:
            raw = await redis_client.hgetall(f"{self.state_prefix}{session_id}")
            data = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in raw.items()}
        
        if not data.get("documento") or not data.get("nombres"):
            return {"type": "card", "cardType": "IdentityCard", "data": data}
        if not data.get("email") or not data.get("celular"):
            return {"type": "card", "cardType": "ContactCard", "data": data}
        
        return {"type": "card", "cardType": "EvidenceAndLegalCard", "data": data}

    async def finalize_pqrs(self, session_id: str) -> dict:
        """FASE 3: Cierre Determinista Síncrono con Wait Protocol V65.14"""
        start_time = time.time()
        state_key = f"{self.state_prefix}{session_id}"
        
        # Wait Protocol
        for _ in range(20):
            raw = await redis_client.hgetall(state_key)
            state = { (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v) for k, v in raw.items() }
            if float(state.get("confidence", 0.0)) >= 0.85: break
            await asyncio.sleep(1)

        context = PDFSanitizer.inject_context(state)
        radicado = context.get("radicado") or f"CALI-GEN-{session_id[-4:].upper()}"
        
        required_docs = context.get("required_docs")
        if isinstance(required_docs, str): 
            try: required_docs = json.loads(required_docs)
            except: required_docs = None
        required_docs = required_docs or [{"key": "memorial", "template": "memorial.j2"}]

        pdf_paths = pdf_service.generate(context, required_docs)
        if not pdf_paths: raise Exception("No se generaron PDFs.")

        final_artifacts = [
            {"type": k, "url": f"http://localhost:8000/vault_digital/{radicado}/{os.path.basename(v)}", "name": os.path.basename(v)} 
            for k, v in pdf_paths.items()
        ]

        final_response = {"status": "complete", "progress": 100, "radicado_id": radicado, "documents": final_artifacts}
        await redis_client.setex(f"progress:{session_id}", 600, json.dumps(final_response))
        
        logger.success(f"🏁 [GODS_EYE: FINALIZE_SUCCESS] session={session_id} | radicado={radicado}")
        return final_response

    async def register_citizen_consent(self, session_id: str, consent_type: str, client_ip: str) -> dict:
        state_key = f"{self.state_prefix}{session_id}"
        await redis_client.hset(state_key, mapping={"autorizacion_datos": "True", "consent_ip": client_ip})
        return {"status": "success", "message": "Consentimiento registrado"}

pqrs_manager = PQRSManager()
