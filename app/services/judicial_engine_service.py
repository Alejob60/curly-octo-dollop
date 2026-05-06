import json
import datetime
import hashlib
import os
import uuid
import base64
import re
from loguru import logger
from app.services.pdf_service import pdf_service
from app.services.signature_service import signature_service
from app.services.traceability_service import traceability_service
from app.services.vault_manager import vault_manager
from app.core.vertex_client import vertex_client
from app.services.conversation_manager import conversation_manager
from app.services.cache_service import cache_service
from app.services.phase_orchestrator import phase_guard, Phase
from app.services.deterministic_extractor import deterministic_extractor
from app.services.user_profile_service import user_profile_service
from app.services.use_case_service import use_case_service
from app.services.use_case_validator import use_case_validator
from app.services.metrics_service import metrics_service
from app.services.privacy_shield_service import privacy_shield
from app.core.config import settings

class JudicialEngineService:
    def __init__(self):
        logger.info("⚖️ Motor Judicial V33.3: Orquestador con Escudo de Privacidad Orbital.")

    async def _analyze_situational_needs(self, issue: str, session_id: str, matched_case: dict = None) -> dict:
        fallback = {"dependencia_id": "4136", "required_docs": ["Identificación"], "analysis_summary": "Requerimiento general."}
        try:
            global_rules = "REGLA GLOBAL: Aplicar Ley 1755 de 2015."
            extra_rules = f"\nREGLAS ESPECÍFICAS: {matched_case['mandatory_citations']}" if matched_case else ""
            prompt = f"{global_rules}\n{extra_rules}\nAnaliza: '{issue}'. Devuelve JSON con 'dependencia_id', 'required_docs' (lista) y 'analysis_summary'."
            res_text = await vertex_client.generate_content([prompt])
            if not res_text or "[FALLO" in res_text: return fallback
            clean_json = res_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception: return fallback

    async def run_multimodal_pqrsd_flow(self, issue: str, history: list, attached_files: list, client_ip: str = "N/A", user_agent: str = "N/A", session_id: str = "default"):
        """
        V33.3: Flujo Directivo con Escudo de Privacidad (Tokenización/Rehidratación).
        """
        try:
            logger.info(f"⚖️ Orquestación V33.3 Shield (Session: {session_id})")
            
            # --- CASO ESPECIAL: INICIO O SALUDO VACÍO ---
            if issue.lower() in ["hola", "inicio", ""] and not history:
                return {
                    "status": "inquiry", "bloque": 0, "phase": "fase_1_identidad",
                    "respuesta_chat": "👋 ¡Hola! Soy el asistente virtual de PQRSD de la **Alcaldía de Santiago de Cali**. Para ayudarte rápido, por favor **escribe en un solo mensaje tu solicitud, queja o reclamo con el mayor detalle posible**.",
                    "data_consolidada": {}
                }

            # 1. ESCUDO DE PRIVACIDAD: Tokenizar entrada para Gemini
            tokenized_issue = await privacy_shield.tokenize_text(session_id, issue)
            
            # 2. ANALISIS CON GEMINI (Sobre texto anonimizado)
            full_history_text = "\n".join([m['content'] for m in history]) + "\n" + tokenized_issue
            extraction_res = await vertex_client.generate_content([f"Analiza e interactúa: {full_history_text}"])
            
            extracted = {}
            try:
                clean_json = extraction_res.replace("```json", "").replace("```", "").strip()
                extracted = json.loads(clean_json)
            except:
                extracted = {"mensaje_ia": "Analizando tu caso...", **deterministic_extractor.extract(full_history_text)}

            # 3. REHIDRATACIÓN: Restaurar datos reales en la respuesta de la IA
            res_ia_anonymized = extracted.get("mensaje_ia", "Perfecto.")
            res_ia = await privacy_shield.rehydrate_text(session_id, res_ia_anonymized)

            # 4. RESCATE DE MEMORIA E IDENTIFICACIÓN EN DB (Usando datos reales)
            # Rehidratar el JSON extraído para validación interna
            extracted_rehydrated = {k: (await privacy_shield.rehydrate_text(session_id, str(v)) if isinstance(v, str) else v) for k,v in extracted.items()}
            
            cc_to_lookup = extracted_rehydrated.get("documento")
            user_profile = {}
            found_in_db = False
            if cc_to_lookup:
                user_profile = await user_profile_service.get_or_create(cc_to_lookup, defaults=extracted_rehydrated)
                if user_profile and user_profile.get("created_at"): found_in_db = True

            # 5. SEÑALES DE CONFIRMACIÓN
            is_b1_confirmed = "BLOQUE 1 COMPLETADO" in issue.upper()
            is_b2_confirmed = "BLOQUE 2 COMPLETADO" in issue.upper()

            # 6. CONSOLIDACIÓN (Single Source of Truth)
            d = {
                "peticionario": {
                    "tipo_solicitante": extracted_rehydrated.get("tipo_solicitante") or "Persona Natural",
                    "tipo_documento": extracted_rehydrated.get("tipo_documento") or "Cedula de Ciudadania",
                    "documento": user_profile.get("cc") or extracted_rehydrated.get("documento") or "PENDIENTE",
                    "nombres": user_profile.get("nombre_completo") or extracted_rehydrated.get("nombres") or "PENDIENTE",
                    "apellidos": extracted_rehydrated.get("apellidos") or "",
                    "found_in_db": found_in_db
                },
                "contacto": {
                    "direccion": user_profile.get("direccion_notificacion") or extracted_rehydrated.get("direccion") or "PENDIENTE",
                    "email": extracted_rehydrated.get("email") or "PENDIENTE",
                    "celular": extracted_rehydrated.get("celular") or "PENDIENTE"
                },
                "hechos": {
                    "tipo_solicitud": extracted_rehydrated.get("tipo_solicitud") or "Derecho de Petición",
                    "asunto": extracted_rehydrated.get("asunto") or "Trámite General",
                    "motivo": tokenized_issue
                }
            }

            # 7. LÓGICA DE DECISIÓN
            if not is_b1_confirmed and (d["peticionario"]["documento"] == "PENDIENTE" or not is_b1_confirmed):
                msg = res_ia if not found_in_db else f"¡Bienvenido de nuevo! He encontrado tus datos. Por favor, confírmalos para continuar con tu **{d['hechos']['tipo_solicitud']}**."
                return {"status": "inquiry", "bloque": 1, "phase": "fase_1_identidad", "respuesta_chat": msg, "data_consolidada": d}

            if not is_b2_confirmed and (d["contacto"]["direccion"] == "PENDIENTE" or not is_b2_confirmed):
                return {"status": "inquiry", "bloque": 2, "phase": "fase_2_ubicacion", "respuesta_chat": f"Gracias {d['peticionario']['nombres']}. Confirma tus datos de contacto.", "data_consolidada": d}

            has_evidence = any(x in issue.upper() for x in ["COMPLETADO", "CARGADOS", "ADJUNTO", "EVIDENCIA"])
            if not has_evidence:
                matched_case = await use_case_service.match_case(full_history_text)
                analysis = await self._analyze_situational_needs(full_history_text, session_id, matched_case)
                return {"status": "inquiry", "bloque": 4, "phase": "fase_3_analisis", "respuesta_chat": f"Análisis: {analysis.get('analysis_summary')}. Carga evidencia.", "data_consolidada": d}

            return {"status": "pending_signature", "phase": "fase_5_generacion", "respuesta_chat": "¡Expediente listo! Procede a firmar.", "data": {"audit_draft": d}, "data_consolidada": d}

        except Exception as e:
            logger.error(f"❌ Error V33.3 Shield: {e}")
            return {"status": "error", "respuesta_chat": "Error en el túnel de privacidad."}

    async def finalize_and_sign_pqrsd(self, audit_data: dict, user_ip: str, session_id: str = None):
        try:
            # 1. GENERACIÓN DE IDENTIFICADOR ÚNICO
            rad_id = f"CALI-SHIELD-{uuid.uuid4().hex[:4].upper()}"
            logger.info(f"🖋️ Iniciando firma de radicado {rad_id} para sesión {session_id}")

            # 2. REHIDRATACIÓN CRÍTICA (Paso final del Túnel de Privacidad)
            # Recuperamos los datos reales de PostgreSQL antes de imprimir el PDF
            nombres_reales = await privacy_shield.rehydrate_text(session_id, audit_data['peticionario']['nombres'])
            motivo_real = await privacy_shield.rehydrate_text(session_id, audit_data['hechos']['motivo'])
            
            # 3. CREACIÓN DE BÚNKER DIGITAL GCS
            paths = vault_manager.create_radicado_container(rad_id, nombres_reales)
            
            # 4. GENERACIÓN DE PDF CON DATOS REALES
            pdf = await pdf_service.generate_grounded_pdf({
                "radicado": rad_id, 
                "citizen_name": nombres_reales, 
                "hechos": motivo_real[:2000], # Ampliamos capacidad de hechos rehidratados
                "legal_tags": ["ley_1755_2015"]
            }, paths)
            
            # 5. SEGURIDAD VOLÁTIL: Limpiar el puente de tokens tras éxito
            if session_id:
                await privacy_shield.cleanup_session(session_id)
            
            return {
                "status": "success", 
                "radicado_id": rad_id, 
                "pdf_url": f"/vault_digital/{os.path.basename(pdf)}", 
                "respuesta_chat": f"¡Trámite Exitoso! Su radicado oficial es el **#{rad_id}**. Puede descargar su PDF certificado en el búnker digital."
            }
        except Exception as e:
            logger.error(f"Fallo Firma Shield: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "error", "respuesta_chat": "Error en el proceso de sellado y rehidratación."}

judicial_engine = JudicialEngineService()
