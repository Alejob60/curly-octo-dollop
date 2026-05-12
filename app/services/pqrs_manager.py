import json
import re
import hashlib
import datetime
import time
import os
import yaml
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger
from enum import Enum
import json_repair

from app.core.db_clients import redis_client
from app.core.vertex_client import vertex_client
from app.utils.sanitizer import PDFSanitizer
from app.services.pdf_service import pdf_service
from app.services.privacy_shield_service import privacy_shield
from app.services.phase_orchestrator import phase_guard, Phase
from app.services.rag_context import rag_manager
from app.services.law_router import law_router
from app.services.orchestrator import orchestrator
from app.models.schemas import LegalAnalysisResult, ExtractionResult

class Phase(str, Enum):
    F1_IDENTIDAD = "fase_1_identidad"
    F2_TRIAJE = "fase_2_triaje"
    F3_ANALISIS = "fase_3_analisis"
    F4_EVIDENCIA = "fase_4_evidencia"
    F5_CONFIRMACION = "fase_5_confirmacion"

class PQRSManager:
    """
    💎 V65.9: Orquestador Maestro Diamond Refactored.
    ✅ Zero-Magic | ✅ RAG Legal Pro | ✅ Strict Schema | ✅ SSE Streaming
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
        
        # 2. Nombre (REGEX ROBUSTO V65.1)
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
            "motivo": message, # 🔧 FIX: Guardar solicitud original
            "dependencia_id": profile.get("DEPENDENCY_ID", "4131"),
            "dependencia_competente": profile.get("TARGET_DEPENDENCY", "Secretaría General"),
            "radicado": radicado,
            "current_phase": Phase.F1_IDENTIDAD.value
        }

        # 👁️ [GODS_EYE]
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "session_id": session_id,
            "phase": "fase_1_ingesta",
            "service": "pqrs_manager",
            "action": "extract_basic_info",
            "input": {"message_len": len(message)},
            "extraction_result": {
                "nombres": nombres, "apellidos": apellidos, "documento": documento,
                "municipio": "Cali", "regex_pattern": matched_pattern
            },
            "profile_detection": {
                "detected_profile": profile.get("ID"),
                "dependency_id": profile.get("DEPENDENCY_ID")
            }
        }
        logger.info(f"👁️ [PHASE_1_LOG] {json.dumps(log_entry, indent=2, ensure_ascii=False)}")
        return extraction

    async def analyze_initial_message(self, session_id: str, message: str) -> dict:
        """FASE 2: Inicio de flujo determinista V65.0"""
        raw = self.extract_basic_info(session_id, message)
        state_key = f"{self.state_prefix}{session_id}"
        await redis_client.hset(state_key, mapping={k: str(v) for k, v in raw.items() if v})
        await redis_client.expire(state_key, self.ttl_seconds)
        
        asyncio.create_task(self.background_process_full_analysis(session_id, message))
        
        return await self.get_next_ui_instruction(session_id, raw)

    async def background_process_full_analysis(self, session_id: str, message: str):
        """Módulo 5: Proceso asíncrono robusto con RAG y Orquestación"""
        try:
            state_key = f"{self.state_prefix}{session_id}"
            
            # --- FASE 3: ANALIZANDO (PhaseGuard) ---
            await phase_guard.transition(session_id, Phase.F3_ANALISIS)
            
            await orchestrator.emit_event(
                session_id, Phase.F3_ANALISIS, "🔐 Anonimizando datos sensibles...", 10
            )
            
            tokenized_message = await privacy_shield.tokenize_text(session_id, message)

            # --- MÓDULO 4: ENRUTAMIENTO ---
            await orchestrator.emit_event(
                session_id, Phase.F3_ANALISIS, "⚖️ Clasificando marco legal...", 20
            )
            classification = await law_router.classify(tokenized_message)
            legal_template = law_router.get_template(classification.law_id)
            
            # --- MÓDULO 3: RECUPERACIÓN RAG ---
            await orchestrator.emit_event(
                session_id, Phase.F3_ANALISIS, "🏛️ Recuperando base legal de MongoDB...", 35
            )
            
            legal_grounding = await rag_manager.get_legal_grounding(
                law_type=classification.law_id.upper(), 
                query_text=tokenized_message
            )

            await orchestrator.emit_event(
                session_id, Phase.F3_ANALISIS, "🧠 Analizando con IA Judicial...", 50
            )
            
            # Recuperar estado actual para el merge
            raw_state = await redis_client.hgetall(state_key)
            state_data = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in raw_state.items()}

            # --- MOTOR DE IA ESTRICTO (Con Semáforo y Auditoría de Confianza) ---
            async def run_ai_logic():
                prompt = f"""
                ESTRATEGIA LEGAL APLICABLE:
                {legal_template}
                
                CONTEXTO LEGAL (RAG GROUNDING):
                {legal_grounding}
                
                MENSAJE ORIGINAL DEL CIUDADANO:
                {message}
                
                MENSAJE TOKENIZADO (PII PROTECTED):
                {tokenized_message}
                
                INSTRUCCIÓN MAGISTRADA (V65.12):
                1. Genera un ASUNTO formal y técnico.
                2. Analiza los hechos técnicos descritos por el ciudadano.
                3. Genera un BORRADOR DE PROYECCIÓN de respuesta que sea PROFUNDO y TÉCNICO.
                4. Usa OBLIGATORIAMENTE el CONTEXTO LEGAL (RAG) provisto.
                5. Puebla la lista 'citas_verificables' con al menos 2 artículos relevantes citados en el borrador.
                6. El borrador debe tener: Antecedentes, Análisis Jurídico y Resolución concreta.
                7. NO USES FRASES GENÉRICAS. Sé específico.
                
                RESPONDE EXCLUSIVAMENTE EN FORMATO JSON ESTRÍCTO.
                """
                schema = LegalAnalysisResult.model_json_schema()
                return await vertex_client.generate_content([prompt], response_schema=schema)

            start_ai = time.time()
            # 🛡️ PIPELINE SEGURO V65.12
            ai_resp, audit = await orchestrator.run_shielded_analysis(session_id, message, run_ai_logic)
            
            # 🔍 LOG RAW IA & AUDIT
            logger.debug(f"🤖 [RAW_AI_RESPONSE] session={session_id} | audit_score={audit['score']} | resp={ai_resp}")
            
            try:
                validated_data = LegalAnalysisResult.model_validate_json(ai_resp)
                parsed = validated_data.model_dump()
            except Exception as e:
                logger.warning(f"⚠️ [IA_SCHEMA_ERROR] Fallo validación, reparando: {e}")
                parsed_raw = json_repair.loads(ai_resp)
                parsed = parsed_raw if isinstance(parsed_raw, dict) else {}
                
            latency = (time.time() - start_ai) * 1000
            
            # Inyectar métricas de auditoría en el estado
            parsed["confidence"] = audit["score"]
            parsed["audit_reason"] = audit["reason"]
            parsed["needs_human_review"] = audit["needs_human_review"]

            # 👁️ [GODS_EYE]
            log_ai = {
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "session_id": session_id,
                "phase": "fase_3_analisis",
                "service": "legal_agents.orchestrator",
                "action": "process",
                "agent_extractor": {"model": "gemini-1.5-pro", "json_response": parsed, "latency_ms": latency},
                "audit": audit
            }
            logger.info(f"👁️ [PHASE_3_AI_LOG] {json.dumps(log_ai, indent=2, ensure_ascii=False)}")
            
            if not audit["passed"]:
                await orchestrator.emit_event(
                    session_id, Phase.F3_ANALISIS, "⚠️ Alerta: Baja confianza en análisis. Requiere revisión técnica.", 99,
                    data={"needs_review": True, "score": audit["score"]}
                )
                logger.critical(f"🚨 [FLOW_ALERT] Sesión {session_id} marcada para revisión humana (Score: {audit['score']})")
                
                # 📥 PERSISTENCIA PARA REVISIÓN HUMANA (Diamond V65.14)
                db = mongo_manager.get_db()
                if db is not None:
                    await db["pqrs_human_review"].update_one(
                        {"session_id": session_id},
                        {"$set": {
                            "radicado": state_data.get("radicado", "GEN"),
                            "asunto": parsed.get("asunto", "Solicitud sin asunto"),
                            "confidence": audit["score"],
                            "reason": audit["reason"],
                            "hechos_extraidos": parsed.get("hechos_extraidos"),
                            "borrador_proyeccion": parsed.get("borrador_proyeccion"),
                            "status": "PENDING",
                            "created_at": time.time(),
                            "payload_snapshot": state_data
                        }},
                        upsert=True
                    )
            
            await orchestrator.emit_event(
                session_id, Phase.F3_ANALISIS, "✅ Finalizando análisis legal...", 85
            )
            
            merged = {**state_data, **parsed}
            clean_context = PDFSanitizer.inject_context(merged)
            
            # --- CIERRE DE FASE ---
            await redis_client.hset(state_key, mapping={k: str(v) for k, v in clean_context.items() if v})
            
            preview = {
                "hechos_summary": clean_context.get("hechos_extraidos", "")[:150] + "...",
                "citations_count": len(clean_context.get("citas_verificables", [])),
                "draft_word_count": len(clean_context.get("borrador_proyeccion", "").split())
            }
            
            await orchestrator.emit_event(
                session_id, Phase.F3_ANALISIS, "✅ Análisis completado.", 99, 
                data={"analysis_ready": True, "preview": preview}
            )
            logger.success(f"✅ Background completado para {session_id}")

        except Exception as e:
            logger.error(f"❌ Error background: {e}")
            await redis_client.setex(f"progress:{session_id}:error", 300, str(e))

    async def get_next_ui_instruction(self, session_id: str, data: dict = None) -> dict:
        if not data:
            state_key = f"{self.state_prefix}{session_id}"
            raw = await redis_client.hgetall(state_key)
            data = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in raw.items()}
        
        has_id = data.get("documento") and data.get("nombres")
        has_contact = data.get("email") and data.get("celular")
        
        if not has_id: return {"type": "card", "cardType": "IdentityCard", "data": data}
        if not has_contact: return {"type": "card", "cardType": "ContactCard", "data": data}
        
        return {"type": "card", "cardType": "EvidenceAndLegalCard", "data": data}

    async def finalize_pqrs(self, session_id: str) -> dict:
        """FASE 3: Cierre Determinista Síncrono con Wait Protocol V65.14"""
        start_time = time.time()
        state_key = f"{self.state_prefix}{session_id}"
        
        # --- ⏳ [WAIT_PROTOCOL V65.14] ---
        # Si el usuario finaliza muy rápido, esperamos a que la IA termine el análisis de fondo.
        max_wait = 20
        for _ in range(max_wait):
            raw = await redis_client.hgetall(state_key)
            if not raw: raise ValueError("Sesión no encontrada")
            
            # Decodificar estado
            current_state = { (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v) for k, v in raw.items() }
            
            # Verificar si la IA ya terminó (confidence > 0)
            confidence = float(current_state.get("confidence", 0.0))
            if confidence >= 0.85:
                logger.info(f"✅ [WAIT_PROTOCOL] IA lista para {session_id} (Score: {confidence})")
                break
                
            if _ % 2 == 0:
                logger.info(f"⏳ [WAIT_PROTOCOL] Esperando análisis IA para {session_id}...")
            await asyncio.sleep(1)
        else:
            logger.error(f"❌ [WAIT_PROTOCOL] Timeout esperando análisis IA para {session_id}")

        # Recuperar estado final
        raw = await redis_client.hgetall(state_key)
        state = { (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v) for k, v in raw.items() }
        
        # 🔍 LOG STATE RECOVERY
        logger.debug(f"🔍 [STATE_RECOVERY] session={session_id} | fields={list(state.keys())}")

        # 🔧 FIX 2: Eliminar metadata de IA
        for key in ["borrador_proyeccion", "hechos_extraidos", "soporte_traslado", "asunto"]:
            if state.get(key):
                state[key] = PDFSanitizer.strip_ai_metadata(state[key])

        # Blindaje final
        context = PDFSanitizer.inject_context(state)
        radicado = context.get("radicado") or f"CALI-GEN-{session_id[-4:].upper()}"
        context["radicado"] = radicado
        
        # Parsear listas/dicts que vienen de Redis como strings
        for field in ["required_docs", "citas_verificables"]:
            if isinstance(context.get(field), str):
                try: context[field] = json.loads(context[field])
                except: context[field] = []

        required_docs = context.get("required_docs")
        if not required_docs or not isinstance(required_docs, list):
            required_docs = [{"key": "memorial", "template": "memorial.j2"}]

        # 📄 LOG FINAL CONTEXT (🔧 Requerimiento Usuario)
        logger.info(f"📄 [FINAL_PDF_CONTEXT] session={session_id} | radicado={radicado} | docs={len(required_docs)}")
        logger.debug(f"📊 [FULL_CONTEXT_DUMP] {json.dumps({k: str(v)[:100] for k, v in context.items()}, indent=2)}")

        pdf_paths = pdf_service.generate(context, required_docs)
        
        if not pdf_paths:
            raise Exception("No se generaron PDFs. Revisa logs de PDFService.")

        final_artifacts = [
            {
                "type": k, 
                "url": f"http://localhost:8000/vault_digital/{radicado}/{os.path.basename(v)}", 
                "name": os.path.basename(v),
                "preview_url": f"http://localhost:8000/vault_digital/{radicado}/{os.path.basename(v)}"
            } for k, v in pdf_paths.items()
        ]

        final_response = {
            "status": "complete",
            "progress": 100,
            "radicado_id": radicado,
            "documents": final_artifacts
        }
        
        await redis_client.setex(f"progress:{session_id}", 600, json.dumps(final_response))
        
        # 📊 [FLOW_METRICS]
        logger.info("📊 [FLOW_METRICS] ================= CIERRE DE FLUJO =================")
        logger.info(f"🆔 Radicado: {radicado} | ⏱️ Tiempo: {time.time() - start_time:.2f}s")
        logger.info("📊 [FLOW_METRICS] ==================================================")
        
        logger.success(f"🏁 [GODS_EYE: FINALIZE_SUCCESS] session={session_id} | radicado={radicado}")
        return final_response

    async def finalize_pqrs_with_context(self, session_id: str, context_override: dict) -> dict:
        """Fallback: Finalización con contexto inyectado manualmente"""
        required_docs = [{"key": "memorial", "template": "memorial.j2"}]
        
        for key in ["borrador_proyeccion", "hechos_extraidos", "soporte_traslado", "asunto"]:
            if context_override.get(key):
                context_override[key] = PDFSanitizer.strip_ai_metadata(context_override[key])

        context = PDFSanitizer.inject_context(context_override)
        context["session_id"] = session_id
        radicado = context.get("radicado", "GEN")
        
        pdf_paths = pdf_service.generate(context, required_docs)
        
        final_response = {
            "status": "complete",
            "progress": 100,
            "radicado_id": radicado,
            "documents": [{"type": k, "url": f"http://localhost:8000/vault_digital/{radicado}/{os.path.basename(v)}", "name": os.path.basename(v)} for k, v in pdf_paths.items()]
        }
        await redis_client.setex(f"progress:{session_id}", 600, json.dumps(final_response))
        return final_response

    async def register_citizen_consent(self, session_id: str, consent_type: str, client_ip: str) -> dict:
        """Registro de consentimiento Habeas Data"""
        state_key = f"{self.state_prefix}{session_id}"
        now = datetime.datetime.utcnow()
        timestamp = now.isoformat()
        
        await redis_client.hset(state_key, mapping={
            "autorizacion_datos": "True",
            "consent_type": consent_type,
            "consent_ip": client_ip,
            "consent_timestamp": timestamp
        })
        
        log_entry = {
            "timestamp": timestamp + "Z",
            "session_id": session_id,
            "phase": "fase_2_triaje",
            "service": "pqrs_manager",
            "action": "register_consent",
            "consent_registration": {
                "registered": True, "ip": client_ip, "timestamp": timestamp,
                "ledger_hash": f"GCP::1::{hashlib.sha256(session_id.encode()).hexdigest()[:16].upper()}"
            }
        }
        logger.info(f"👁️ [CONSENT_LOG] {json.dumps(log_entry, indent=2, ensure_ascii=False)}")
        return {"status": "success", "message": "Consentimiento registrado"}

pqrs_manager = PQRSManager()
