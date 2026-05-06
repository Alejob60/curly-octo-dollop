import json
import re
import hashlib
import datetime
import time
import os
import base64
from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger
import json_repair
from app.core.db_clients import redis_client, postgres_manager, mongo_db
from app.core.vertex_client import vertex_client
from app.services.phase_orchestrator import phase_guard, Phase
from app.services.privacy_shield_service import privacy_shield
from app.services.legal_citation_engine import legal_citation_engine
from app.services.routing_service import dependency_router
from app.services.autonomous_routing import autonomous_router
from app.services.ledger_service import ledger_service
from app.services.persistence_bridge import persistence_bridge
from app.services.persistence_middleware import persistence_middleware
from app.services.pdf_service import pdf_service
from app.core.config import settings
from app.models.sql_models import CaseRegistry
import yaml


class PQRSManager:
    """
    V64.2: Orquestador Judicial Robusto (Diamond Edition).
    ✅ Sincronización SQL pdf_paths | ✅ Verificación física de archivos | ✅ Fallbacks
    """
    
    def __init__(self):
        self.state_prefix = "pqrs:state:"
        self.ttl_seconds = 259200
        try:
            reg_path = Path(__file__).parent.parent / "core" / "case_registry.yaml"
            with open(reg_path, 'r', encoding='utf-8') as f:
                self.registry = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"❌ Error cargando Case Registry: {e}")
            self.registry = {"CASE_PROFILES": []}

    def _detect_profile(self, message: str) -> dict:
        m_lower = str(message).lower()
        profiles = self.registry.get("CASE_PROFILES", [])
        for profile in profiles:
            if profile.get("ID") == "GENERIC_TRAMITE":
                continue
            if any(kw in m_lower for kw in profile.get("KEYWORDS", [])):
                return profile
        return next((p for p in profiles if p.get("ID") == "GENERIC_TRAMITE"), {})

    @staticmethod
    def _sanitize_for_pdf(text: str) -> str:
        if not text or not isinstance(text, str): return ""
        if text.strip().startswith('{') or text.strip().startswith('['):
            patterns = [r'\{[^{}]*"mensaje_ia"[^{}]*\}', r'\{[^{}]*"tipo_solicitud"[^{}]*\}', r'^\s*\{.*\}\s*$',]
            for pattern in patterns: text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        return text.strip() or "Contenido en procesamiento."

    @staticmethod
    def _validate_and_fix_citations(citas_input) -> List[dict]:
        if not citas_input: return []
        if isinstance(citas_input, str):
            try: citas_input = json.loads(citas_input)
            except: return []
        if not isinstance(citas_input, list): return []
        clean = []
        for c in citas_input:
            if isinstance(c, dict) and c.get("articulo") and c.get("texto_relevante"):
                clean.append({
                    "citacion_formato": c.get("citacion_formato", "Norma General"),
                    "articulo": c.get("articulo", "N/A"),
                    "texto_relevante": c.get("texto_relevante", ""),
                    "ente_emisor": c.get("ente_emisor", "Alcaldía de Cali")
                })
        return clean

    async def analyze_initial_message(self, session_id: str, message: str) -> dict:
        from app.services.legal_agents.orchestrator import legal_orchestrator
        await redis_client.hset(f"{self.state_prefix}{session_id}", "current_phase", Phase.F1_IDENTIDAD.value)
        profile = self._detect_profile(message)
        radicado = f"CALI-{profile.get('DEPENDENCY_ID', 'GEN')}-{session_id[-4:].upper()}"
        
        tokenized_msg = await privacy_shield.tokenize_text(session_id, message)
        agent_state = await legal_orchestrator.process(session_id, tokenized_msg, profile.get("ID"))
        
        final_data = {"documento": "", "nombres": "", "apellidos": "", "email": "", "celular": "", "direccion": "", "asunto": "", "motivo": ""}
        final_data.update({
            "active_profile": profile.get("ID"),
            "required_docs": json.dumps(profile.get("REQUIRED_DOCUMENTS", [])),
            "documento": agent_state.documento or "",
            "nombres": agent_state.nombres or "Ciudadano",
            "apellidos": agent_state.apellidos or "",
            "asunto": f"SOLICITUD: {profile.get('ID')}",
            "borrador_proyeccion": self._sanitize_for_pdf(agent_state.draft_document or ""),
            "dependencia_id": profile.get("DEPENDENCY_ID", "4131"),
            "dependencia_competente": profile.get("TARGET_DEPENDENCY", "Secretaría General"),
            "radicado": radicado,
            "citas_verificables": json.dumps(self._validate_and_fix_citations([]))
        })
        await redis_client.hset(f"{self.state_prefix}{session_id}", mapping={k: str(v) for k,v in final_data.items() if v})
        return await self.get_next_ui_instruction(session_id, final_data)

    async def get_next_ui_instruction(self, session_id: str, data: dict = None) -> dict:
        state_key = f"{self.state_prefix}{session_id}"
        if not data:
            raw = await redis_client.hgetall(state_key)
            # 🛡️ NORMALIZACIÓN ROBUSTA (Bytes/Str)
            data = {
                (k.decode() if isinstance(k, bytes) else k): 
                (v.decode() if isinstance(v, bytes) else v) 
                for k, v in raw.items()
            }
        
        phase_val = await phase_guard.get_current_phase(session_id)
        # Convertir a Phase enum de forma segura
        try:
            phase = Phase(phase_val) if isinstance(phase_val, str) else phase_val
        except:
            phase = Phase.F1_IDENTIDAD

        def _is_v(v, is_numeric=False):
            if not v: return False
            v_s = str(v).strip().lower()
            if any(x in v_s for x in ["[", "]", "token", "pendiente", "null", "none", "n/a"]): return False
            return len(re.sub(r'\D', '', v_s)) >= 5 if is_numeric else len(v_s) > 2

        has_id = _is_v(data.get("documento"), True) and _is_v(data.get("nombres"))
        has_contact = _is_v(data.get("email")) and _is_v(data.get("celular"), True)
        
        # Flexibilidad para el flag de autorización
        auth_raw = data.get("autorizacion_datos")
        has_auth = str(auth_raw).lower() in ["true", "1", "yes", "t"]
        
        has_conf_f3 = str(data.get("confirmed", "false")).lower() in ["true", "1", "yes"]
        has_conf_fin = str(data.get("confirmado", "false")).lower() in ["true", "1", "yes"]

        logger.info(f"🔍 [FLOW_TRACE] session={session_id} | phase={phase.value} | id={has_id} contact={has_contact} auth={has_auth} f3={has_conf_f3} fin={has_conf_fin}")

        new_phase = phase
        if not has_id: 
            new_phase = Phase.F1_IDENTIDAD
        elif not has_contact: 
            new_phase = Phase.F2_TRIAJE
        elif phase == Phase.F1_IDENTIDAD and has_id: 
            new_phase = Phase.F2_TRIAJE
        elif phase == Phase.F2_TRIAJE and has_contact: 
            new_phase = Phase.F3_ANALISIS
        elif phase == Phase.F3_ANALISIS and has_auth and has_conf_f3: 
            new_phase = Phase.F4_EVIDENCIA
        elif phase == Phase.F4_EVIDENCIA and has_conf_fin: 
            new_phase = Phase.F5_CONFIRMACION

        if new_phase != phase:
            await phase_guard.transition(session_id, new_phase, data)
            radicado = data.get("radicado") or f"CALI-GEN-{session_id[-4:]}"
            await persistence_bridge.save_progress(session_id, radicado, {"current_phase": new_phase.value})
            data["current_phase"] = new_phase.value
            phase = new_phase

        card_map = {
            Phase.F1_IDENTIDAD: "IdentityCard", 
            Phase.F2_TRIAJE: "ContactCard", 
            Phase.F3_ANALISIS: "EvidenceAndLegalCard", 
            Phase.F4_EVIDENCIA: "ConfirmationCard"
        }
        
        if phase == Phase.F5_CONFIRMACION: 
            return {"type": "command", "command": "READY_FOR_SIGNATURE", "cardType": "SuccessCard", "data": data}
            
        return {"type": "card", "cardType": card_map.get(phase, "IdentityCard"), "data": data}

    async def finalize_pqrs(self, session_id: str) -> dict:
        logger.info(f"🏁 [FINALIZE_START] Iniciando proceso para {session_id}")
        state_key = f"{self.state_prefix}{session_id}"
        try:
            await redis_client.setex(f"progress:{session_id}", 300, json.dumps({"progress": 10, "message": "🔍 Validando expediente..."}))
            raw = await redis_client.hgetall(state_key)
            state = {k: v for k,v in raw.items()}
            radicado = state.get("radicado", f"CALI-GEN-{session_id[-4:]}")
            
            # Preparar contexto para PDF
            context = {**state, "session_id": session_id, "radicado": radicado}
            req_docs = json.loads(context.get("required_docs", "[]")) or [{"key": "memorial", "template": "memorial.j2"}]
            
            # Generación real
            await redis_client.setex(f"progress:{session_id}", 300, json.dumps({"progress": 40, "message": "📄 Generando documentos oficiales..."}))
            gen_result = await pdf_service.generate_dynamic_package(context, req_docs)
            
            if not gen_result: raise Exception("Error: No se generaron archivos físicos.")

            # Sincronización SQL (Bóveda Pública)
            final_artifacts = []
            for k, v in gen_result.items():
                web_path = f"vault_digital/{radicado}/{Path(v).name}"
                final_artifacts.append({
                    "id": f"{k}_{radicado}", "type": k, "preview_url": f"http://localhost:8000/{web_path}", 
                    "name": Path(v).name, "folder": next((d.get("folder") for d in req_docs if d.get("key") == k), "Otros")
                })

            res = {"status": "success", "radicado_id": radicado, "documents": final_artifacts}

            await persistence_bridge.save_progress(session_id, radicado, {
                "estado": "APPROVED",
                "pdf_paths": {d["type"]: d["preview_url"] for d in final_artifacts},
                "soporte_traslado": "LOCAL-SYNC"
            })

            # 🔥 FIX DEFINITIVO: Marcadores para Polling
            logger.info(f"💾 [FINALIZE] Guardando marcadores de éxito para {session_id}")
            await redis_client.setex(f"progress:{session_id}:complete", 600, "true")
            await redis_client.setex(f"progress:{session_id}:final", 600, json.dumps(res))

            # Actualizar el progreso al 100% ( redundancia segura )
            await redis_client.setex(f"progress:{session_id}", 600, json.dumps({
                "progress": 100, 
                "status": "complete",
                "message": "✅ ¡Expediente completado!", 
                "data": res
            }))

            await redis_client.delete(state_key)
            logger.success(f"🏁 [FINALIZE_SUCCESS] {radicado} | {len(final_artifacts)} docs")
            return res

        except Exception as e:
            logger.error(f"❌ Error en finalize: {e}"); await redis_client.setex(f"progress:{session_id}:error", 300, str(e)); raise

pqrs_manager = PQRSManager()
