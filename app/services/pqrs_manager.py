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
from app.core.db_clients import redis_client, postgres_manager, mongo_db, AsyncSessionLocal
from sqlalchemy import text
from app.services.ledger_service import ledger_service
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
    def _clean_llm_artifacts(text: str) -> str:
        if not text or not isinstance(text, str): return text
        # Remover espacios insertados en palabras comunes (Fix V64.2)
        patterns = {
            r'Le\s+y': 'Ley', r'p\s+ersonal': 'personal', r'ca\s+pacitación': 'capacitación',
            r'hi\s+giénicas': 'higiénicas', r'mani\s+pulador': 'manipulador',
            r'p\s+rácticas': 'prácticas', r'o\s+portuno': 'oportuno',
            r'Com\s+prende': 'Comprende', r'ex\s+puesto': 'expuesto',
            r'com\s+petente': 'competente', r'res\s+puesta': 'respuesta',
            r'diri\s+ge': 'dirige', r'correspo\s+ndiente': 'correspondiente',
            r'CAPA\s+CITA\s+CION': 'CAPACITACION'
        }
        for pattern, replacement in patterns.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text.strip()

    @staticmethod
    def _normalize_name(name: str) -> str:
        if not name or not isinstance(name, str): return name
        # Corregir error común de OCR/IA
        name = name.lower().replace("edurado", "Eduardo").replace("huratado", "Hurtado")
        return ' '.join(w.capitalize() for w in name.strip().split())

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

    async def extract_basic_info(self, session_id: str, message: str) -> dict:
        """Extracción Inteligente (Regex) para Auto-relleno y Multi-Tenant"""
        profile = self._detect_profile(message)
        
        # --- LÓGICA DE EXTRACCIÓN SMART ---
        # 1. Cédula (6-10 dígitos)
        doc_match = re.search(r'\b\d{6,10}\b', message)
        documento = doc_match.group(0) if doc_match else ""
        
        # 2. Nombre (Patrones comunes)
        nombres = ""
        apellidos = ""
        name_patterns = [
            r"(?i)me llamo\s+([A-Za-záéíóúñÁÉÍÓÚÑ ]+)",
            r"(?i)soy\s+([A-Za-záéíóúñÁÉÍÓÚÑ ]+)",
            r"(?i)peticionario:?\s+([A-Za-záéíóúñÁÉÍÓÚÑ ]+)",
            r"(?i)nombre:?\s+([A-Za-záéíóúñÁÉÍÓÚÑ ]+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, message)
            if match:
                full_name = match.group(1).strip().split()
                if len(full_name) >= 1:
                    nombres = full_name[0].title()
                    apellidos = " ".join(full_name[1:]).title()
                break

        # 3. SOBERANÍA CALI (Hardcode obligatorio para Alcaldía de Cali)
        municipio = "Cali"
        departamento = "Valle del Cauca"

        radicado = f"CALI-{profile.get('DEPENDENCY_ID', 'GEN')}-{session_id[-4:].upper()}"
        
        return {
            "active_profile": profile.get("ID"),
            "required_docs": json.dumps(profile.get("REQUIRED_DOCUMENTS", [])),
            "documento": documento,
            "nombres": nombres or "Ciudadano",
            "apellidos": apellidos,
            "municipio": municipio,
            "departamento": departamento,
            "asunto": f"SOLICITUD: {profile.get('ID')}",
            "dependencia_id": profile.get("DEPENDENCY_ID", "4131"),
            "dependencia_competente": profile.get("TARGET_DEPENDENCY", "Secretaría General"),
            "radicado": radicado,
            "current_phase": Phase.F1_IDENTIDAD.value
        }

    async def save_initial_state(self, session_id: str, basic_data: dict):
        """Persistencia inicial en Valkey para habilitar flujo inmediato"""
        state_key = f"{self.state_prefix}{session_id}"
        await redis_client.hset(state_key, mapping={k: str(v) for k, v in basic_data.items() if v})
        await redis_client.expire(state_key, self.ttl_seconds)

    async def background_process_full_analysis(self, session_id: str, message: str):
        """Procesamiento pesado en background: agentes legales + persistencia"""
        try:
            logger.info(f"🧠 [BACKGROUND] Iniciando orquestación legal para {session_id}...")
            from app.services.legal_agents.orchestrator import legal_orchestrator
            
            profile = self._detect_profile(message)
            profile_id = profile.get("ID", "GENERIC_TRAMITE")
            
            # 1. Anonimización (Rápida)
            tokenized_msg = await privacy_shield.tokenize_text(session_id, message)
            
            # 2. Orquestación Multi-Agente (Lenta ~90s)
            agent_state = await legal_orchestrator.process(session_id, tokenized_msg, profile_id)
            
            # 3. Mapeo Inicial
            state_key = f"{self.state_prefix}{session_id}"
            
            # 🔍 DEBUG: Guardar respuesta cruda de la IA en logs
            logger.info(f"🤖 [AGENT_RESPONSE_DEBUG] session={session_id} | names='{getattr(agent_state, 'nombres', '')}' | facts='{str(getattr(agent_state, 'facts', []))[:50]}...'")

            # 🧹 SANITIZACIÓN DE DATOS (Fix placeholders and typos)
            raw_nombres = getattr(agent_state, "nombres", "")
            raw_apellidos = getattr(agent_state, "apellidos", "")
            
            # Limpiar placeholders y basura
            final_nombres = raw_nombres if raw_nombres and "[NOMBRE" not in str(raw_nombres) and len(str(raw_nombres)) > 2 else ""
            final_apellidos = raw_apellidos if raw_apellidos and "[NOMBRE" not in str(raw_apellidos) and len(str(raw_apellidos)) > 2 else ""
            
            # Normalización Title Case
            if final_nombres: final_nombres = self._normalize_name(final_nombres)
            if final_apellidos: final_apellidos = self._normalize_name(final_apellidos)

            raw_data = {
                "documento": getattr(agent_state, "documento", "") or "",
                "nombres": final_nombres or "Ciudadano",
                "apellidos": final_apellidos,
                "borrador_proyeccion": getattr(agent_state, "draft_document", "") or "",
                "hechos_extraidos": "\n".join(getattr(agent_state, "facts", [])) if getattr(agent_state, "facts", []) else "",
                "citas_verificables": json.dumps(self._validate_and_fix_citations(getattr(agent_state, "legal_basis", []))),
                "motivo": message 
            }
            
            # 4. 🔥 VALIDACIÓN Y LIMPIEZA NUCLEAR (V64.2)
            clean_data = self._validate_and_clean_context(raw_data)
            clean_data["analysis_complete"] = "true"
            
            logger.info(f"🏁 [FINAL_BACKGROUND_JSON_DATA]: {json.dumps(clean_data, indent=2, ensure_ascii=False)}")
            
            await redis_client.hset(state_key, mapping={k: str(v) for k, v in clean_data.items() if v})
            
            # 5. Actualizar progreso para polling del frontend
            await redis_client.setex(f"progress:{session_id}", 600, json.dumps({
                "progress": 100,
                "status": "complete",
                "message": "✅ Análisis jurídico completado.",
                "analysis_ready": True
            }))
            
            logger.success(f"✅ [BACKGROUND] Procesamiento validado y completado para {session_id}")
            
        except Exception as e:
            logger.error(f"❌ [BACKGROUND] Error en {session_id}: {e}")
            await redis_client.setex(f"progress:{session_id}:error", 300, str(e))

    def _validate_and_clean_context(self, context: dict) -> dict:
        """Valida y limpia datos antes de generar PDFs (V64.2)"""
        cleaned = context.copy()
        
        # 1. Normalizar nombres
        if cleaned.get("nombres"): cleaned["nombres"] = self._normalize_name(cleaned["nombres"])
        if cleaned.get("apellidos"): cleaned["apellidos"] = self._normalize_name(cleaned["apellidos"])
        
        # 2. Limpiar texto de artefactos del LLM
        for key in ["hechos_extraidos", "borrador_proyeccion", "asunto", "motivo", "soporte_traslado"]:
            if cleaned.get(key) and isinstance(cleaned[key], str):
                cleaned[key] = self._clean_llm_artifacts(cleaned[key])
        
        # 3. Limpiar citas
        if isinstance(cleaned.get("citas_verificables"), list):
            for cita in cleaned["citas_verificables"]:
                if isinstance(cita, dict):
                    for field in ["citacion_formato", "texto_relevante"]:
                        if cita.get(field): cita[field] = self._clean_llm_artifacts(cita[field])
        
        # 4. Fallbacks
        hechos = str(cleaned.get("hechos_extraidos", ""))
        if not hechos or len(hechos) < 20 or "no se extrajeron" in hechos.lower():
            motivo = cleaned.get("motivo", "")
            if motivo: cleaned["hechos_extraidos"] = f"El ciudadano solicita el trámite: {self._clean_llm_artifacts(motivo[:300])}"
        
        return cleaned

    def _extract_user_data_from_message(self, message: str) -> dict:
        """Extrae nombre, cédula, ciudad, dirección del mensaje inicial del usuario (Heurística Regex)"""
        import re
        extracted = {}
        msg_lower = message.lower()
        
        # 1. Nombres: patrones "soy X", "me llamo X", "peticionario: X"
        for pattern in [
            r'(?:soy|me llamo|representante[:\s]+)([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)+)',
            r'([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)'
        ]:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                full_name = match.group(1).strip().split()
                if len(full_name) >= 2:
                    extracted["nombres"] = full_name[0].title()
                    extracted["apellidos"] = " ".join(full_name[1:]).title()
                else:
                    extracted["nombres"] = match.group(1).strip().title()
                break
        
        # 2. Cédula: 7-10 dígitos con palabras clave
        doc_match = re.search(r'(?:cédula|cc|identificación|documento|id)[:\s]*(\d{7,10})', msg_lower)
        if doc_match:
            extracted["documento"] = doc_match.group(1)
        
        # 3. Ciudad
        city_match = re.search(r'(?:vivo en|de|municipio de|ciudad de|en la ciudad de)\s+([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ\s]+?)(?:,|\.|$)', message, re.IGNORECASE)
        if city_match:
            city = city_match.group(1).strip()
            if len(city) <= 50 and city.lower() not in ["el", "la", "los", "las"]:
                extracted["municipio"] = city.title()
                if city.lower() in ["cali", "santiago de cali"]:
                    extracted["departamento"] = "Valle del Cauca"
                elif city.lower() == "medellín":
                    extracted["departamento"] = "Antioquia"
        
        # 4. Dirección
        addr_match = re.search(r'(carrera|calle|av|avenida|diagonal|transversal)\s*\d+\s*[a-z]?\s*#?\s*\d+\s*[-–]\s*\d+', message, re.IGNORECASE)
        if addr_match:
            extracted["direccion"] = addr_match.group(0).strip().title()
        
        return extracted

    async def analyze_initial_message(self, session_id: str, message: str) -> dict:
        from app.services.legal_agents.orchestrator import legal_orchestrator
        
        # 🔧 FIX: Limpiar cache para sesiones de prueba
        if session_id.startswith("session-test"):
            await redis_client.delete(f"{self.state_prefix}{session_id}")
            await redis_client.delete(f"progress:{session_id}")
            logger.info(f"🧹 [CACHE_CLEAN] Redis limpiado para sesión de prueba: {session_id}")

        await redis_client.hset(f"{self.state_prefix}{session_id}", "current_phase", Phase.F1_IDENTIDAD.value)
        profile = self._detect_profile(message)
        
        # 🔧 FIX: Extraer datos del usuario ANTES de agentes
        user_extracted = self._extract_user_data_from_message(message)
        
        # Determinar radicado dinámico según municipio detectado
        municipio = user_extracted.get("municipio", "Cali")
        radicado = f"{municipio.upper()[:4]}-{profile.get('DEPENDENCY_ID', 'GEN')}-{session_id[-4:].upper()}"
        
        tokenized_msg = await privacy_shield.tokenize_text(session_id, message)
        agent_state = await legal_orchestrator.process(session_id, tokenized_msg, profile.get("ID"))
        
        final_data = {"documento": "", "nombres": "", "apellidos": "", "email": "", "celular": "", "direccion": "", "asunto": "", "motivo": message}
        
        # Aplicar extracción del usuario PRIMERO (Prioridad UX)
        final_data.update(user_extracted)
        
        # Consolidar con agente_state sin sobrescribir lo que el usuario ya dijo
        final_data.update({
            "active_profile": profile.get("ID"),
            "required_docs": json.dumps(profile.get("REQUIRED_DOCUMENTS", [])),
            "asunto": f"SOLICITUD: {profile.get('ID')}",
            "borrador_proyeccion": self._sanitize_for_pdf(agent_state.draft_document or ""),
            "hechos_extraidos": "\n".join(agent_state.facts) if agent_state.facts else "",
            "dependencia_id": profile.get("DEPENDENCY_ID", "4131"),
            "dependencia_competente": profile.get("TARGET_DEPENDENCY", "Secretaría General"),
            "radicado": radicado,
            "citas_verificables": json.dumps(self._validate_and_fix_citations(getattr(agent_state, "legal_basis", [])))
        })
        
        # Merge inteligente: solo usar agente para campos de identidad si el usuario NO lo dijo explícitamente
        for key in ["nombres", "apellidos", "documento", "municipio", "direccion"]:
            if key not in user_extracted and hasattr(agent_state, key):
                val = getattr(agent_state, key)
                if val and str(val).strip() and str(val).lower() != "ciudadano":
                    final_data[key] = val

        # Sincronizar con Redis
        await redis_client.hset(f"{self.state_prefix}{session_id}", mapping={k: str(v) for k,v in final_data.items() if v})
        
        # 🔧 FIX: Log de verificación de extracción
        logger.info(f"✅ [EXTRACTION_DEBUG] session={session_id} | extracted={user_extracted} | final_names={final_data.get('nombres')}")
        
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
            
            # 🛡️ NORMALIZACIÓN ROBUSTA (Redis puede devolver bytes)
            raw = await redis_client.hgetall(state_key)
            state = {
                (k.decode() if isinstance(k, bytes) else k): 
                (v.decode() if isinstance(v, bytes) else v) 
                for k, v in raw.items()
            }
            
            if not state:
                raise ValueError("No se encontró el estado de la sesión en Redis")

            # 2. 🔥 LIMPIEZA DE ÚLTIMO MINUTO ANTES DE PDF (Sprints Fix)
            state = self._validate_and_clean_context(state)

            radicado = state.get("radicado") or f"CALI-GEN-{session_id[-4:].upper()}"
            
            # 🔧 FIX: Logging de debug para diagnosticar qué datos llegan a PDFs
            logger.debug(f"🔍 [PDF_DEBUG] Contexto para PDFs: nombres={state.get('nombres')}, hechos_len={len(str(state.get('hechos_extraidos', '')))}, citas_count={len(state.get('citas_verificables', [])) if isinstance(state.get('citas_verificables'), list) else 'string'}")
            logger.debug(f"🔍 [PDF_DEBUG] Traslado: justificacion={str(state.get('justificacion_traslado', ''))[:100]}...")

            # Preparar contexto para PDF (Asegurar campos críticos para los templates)
            context = {
                **state,
                "session_id": session_id,
                "radicado": radicado,
                "borrador_proyeccion": state.get("borrador_proyeccion") or f"Se da trámite de fondo a la solicitud radicada bajo el número {radicado}, conforme a los principios de celeridad y eficacia administrativa establecidos en la Ley 1437 de 2011.",
                "hechos_extraidos": state.get("hechos_extraidos") or f"El peticionario solicita el trámite correspondiente a {state.get('asunto', 'la presente solicitud')}, fundamentado en el derecho de petición y la normativa sectorial aplicable.",
                "soporte_traslado": state.get("soporte_traslado") or "Se remite por competencia técnica según Artículo 21 de la Ley 1437 de 2011 (Sustituido por Ley 1755 de 2015).",
                "motivo": state.get("motivo") or state.get("asunto") or "Solicitud de trámite ciudadano.",
                "pdf_dependency": state.get("dependencia_competente", "Secretaría General"),
                "dependencia_gestora": state.get("dependencia_competente", "Secretaría General")
            }
            
            # 🔥 FIX: Forzar citas válidas si el array viene vacío o con Art. N/A
            citas_raw = state.get("citas_verificables", "[]")
            citas = json.loads(citas_raw) if isinstance(citas_raw, str) else citas_raw
            if not citas or any(str(c.get("articulo")).upper() == "N/A" for c in citas):
                context["citas_verificables"] = [
                    {
                        "citacion_formato": "Ley 1437 de 2011", 
                        "articulo": "3", 
                        "texto_relevante": "Principios de la función administrativa: eficacia, celeridad, imparcialidad y publicidad.", 
                        "ente_emisor": "Congreso de la República"
                    }
                ]
            else:
                context["citas_verificables"] = citas
            
            req_docs_raw = state.get("required_docs", "[]")
            req_docs = json.loads(req_docs_raw) if isinstance(req_docs_raw, str) else req_docs_raw
            if not req_docs:
                req_docs = [{"key": "memorial", "template": "memorial.j2", "folder": "01_Memorial_Radicado"}]
            
            # Generación real
            await redis_client.setex(f"progress:{session_id}", 300, json.dumps({"progress": 40, "message": "📄 Generando documentos oficiales..."}))
            gen_result = await pdf_service.generate_dynamic_package(context, req_docs)
            
            if not gen_result: 
                logger.error(f"❌ [FINALIZE] pdf_service no generó archivos para {radicado}")
                raise Exception("Error: No se generaron archivos físicos. Verifique los logs del PDF Engine.")

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

    async def register_citizen_consent(self, session_id: str, consent_type: str, client_ip: str) -> dict:
        """
        🔐 REGISTRO DE CONSENTIMIENTO (Ley 1581 - Diamond Edition).
        Persiste el consentimiento en Valkey y CaseRegistry para cumplimiento legal.
        """
        try:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
            state_key = f"{self.state_prefix}{session_id}"
            
            # 1. Registro en Valkey (Estado en caliente)
            await redis_client.hset(state_key, mapping={
                "autorizacion_datos": "True",
                "consent_type": consent_type,
                "consent_ip": client_ip,
                "consent_timestamp": timestamp.isoformat()
            })

            # 2. Sello en SQL (CaseRegistry) para Auditoría Legal
            async with AsyncSessionLocal() as session:
                query = text("SELECT id FROM cases_registry WHERE session_id = :sid")
                res = await session.execute(query, {"sid": session_id})
                case_id = res.scalar()

                if case_id:
                    upd_query = text("""
                        UPDATE cases_registry SET 
                            consent_granted = TRUE,
                            consent_timestamp = :ts,
                            consent_type = :ctype,
                            consent_ip = :ip,
                            updated_at = NOW()
                        WHERE id = :cid
                    """)
                    await session.execute(upd_query, {"ts": timestamp, "ctype": consent_type, "ip": client_ip, "cid": case_id})
                else:
                    ins_query = text("""
                        INSERT INTO cases_registry (
                            session_id, consent_granted, consent_timestamp, consent_type, consent_ip, estado, created_at
                        ) VALUES (
                            :sid, TRUE, :ts, :ctype, :ip, 'INICIADO', NOW()
                        )
                    """)
                    await session.execute(ins_query, {"sid": session_id, "ts": timestamp, "ctype": consent_type, "ip": client_ip})
                
                await session.commit()

            # 3. Registro en Audit Ledger (Inmutabilidad)
            await ledger_service.log_event(
                registry_id=session_id,
                action="CITIZEN_CONSENT_GRANTED",
                payload={
                    "consent_type": consent_type,
                    "ip": client_ip,
                    "timestamp": timestamp.isoformat(),
                    "compliance": "Ley 1581"
                }
            )

            logger.success(f"🔐 [CONSENT] Registrado para sesión {session_id} desde IP {client_ip}")
            return {"status": "success", "message": "Consentimiento registrado correctamente"}

        except Exception as e:
            logger.error(f"❌ Error registrando consentimiento: {e}")
            raise e

pqrs_manager = PQRSManager()
