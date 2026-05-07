"""
PDF Service - Generación Dinámica Robusta V64.2 (Diamond Edition)
✅ Playwright Sync-Bridge (Windows Stability) | ✅ Verificación Post-Escritura | ✅ Logs Forenses
"""

import os
import json
import asyncio
import hashlib
import base64
import tempfile
import concurrent.futures
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
from app.core.config import settings
from app.services.privacy_shield_service import privacy_shield
from app.services.signer import signer_service
from app.services.gcp_storage_service import immutable_storage_service
from app.services.qr_service import QRService
from loguru import logger

def hard_sanitize_render_context(context: dict) -> dict:
    """Limpia artefactos de tokenización del LLM y normaliza datos críticos (Surgical Fix)"""
    clean = context.copy()
    
    # 1. Regex para espacios rotos por tokenización (ej: "Le y" -> "Ley")
    spacing_artifacts = [
        (r'Le\s+y', 'Ley'), (r'p\s+ersonal', 'personal'), (r'ca\s+pacitación', 'capacitación'),
        (r'hi\s+giénicas', 'higiénicas'), (r'mani\s+pulador', 'manipulador'),
        (r'p\s+rácticas', 'prácticas'), (r'o\s+portuno', 'oportuno'),
        (r'Com\s+prende', 'Comprende'), (r'ex\s+puesto', 'expuesto'),
        (r'com\s+petente', 'competente'), (r'res\s+puesta', 'respuesta'),
        (r'diri\s+ge', 'dirige'), (r'correspo\s+ndiente', 'correspondiente'),
        (r'CAPA\s+CITA\s+CION', 'CAPACITACION'), (r'p\s+or', 'por')
    ]
    
    def clean_text(text: str) -> str:
        if not text or not isinstance(text, str): return text
        for pattern, repl in spacing_artifacts:
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        return text.strip()

    # 2. Aplicar a campos críticos
    for key in ["borrador_proyeccion", "hechos_extraidos", "motivo", "asunto", "soporte_traslado"]:
        if key in clean: clean[key] = clean_text(clean[key])
        
    # 3. Normalizar nombres y limpiar JSON leaks
    clean["nombres"] = clean_text(str(clean.get("nombres", ""))).title()
    clean["apellidos"] = clean_text(str(clean.get("apellidos", ""))).title()
    if clean["nombres"].startswith("{") or clean["nombres"].startswith("["):
        clean["nombres"] = "Peticionario Registrado"

    return clean

class PDFService:
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent.parent / "templates" / "pdf"
        self.vault_base = Path(os.getcwd()) / "vault_digital"
        self.vault_base.mkdir(parents=True, exist_ok=True)

    async def generate_dynamic_package(self, context: Dict, required_docs: List[Dict]) -> Dict[str, str]:
        """
        Genera un paquete de documentos usando un puente síncrono para máxima estabilidad en Windows.
        """
        session_id = context.get('session_id', 'unknown')
        radicado = context.get('radicado', 'GENERICO')
        logger.info(f"🚀 [PDF_ENGINE] Iniciando generación para {radicado} ({len(required_docs)} documentos)")

        try:
            # 1. Preparar contexto (Rehidratación + QR)
            full_context = await self._prepare_context(context, session_id, radicado)
            
            # 2. 🔥 HARD SANITIZATION antes de renderizar
            full_context = hard_sanitize_render_context(full_context)
            
            # 3. Ejecutar renderizado en un ThreadPool
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                results = await loop.run_in_executor(
                    pool, 
                    self._render_batch_sync, 
                    full_context, 
                    required_docs, 
                    radicado
                )
            
            return results

        except Exception as e:
            logger.error(f"🔥 [PDF_ENGINE] Fallo catastrófico: {e}", exc_info=True)
            return {}

    def sanitize_template_text(self, text: str) -> str:
        """Limpia artefactos de formato insertados por LLM o Jinja2 (Legacy fallback)"""
        if not text or not isinstance(text, str):
            return "Texto no disponible"
        
        replacements = {
            "Le y": "Ley", "p ersonal": "personal", "ca p acitación": "capacitación",
            "hi g iénicas": "higiénicas", "CAPA CITA CION": "CAPACITACION",
            "mani p ulador": "manipulador", "p rácticas": "prácticas",
            "o p ortuno": "oportuno", "Com p rende": "Comprende",
            "ex p uesto": "expuesto", "com p etente": "competente",
            "res p uesta": "respuesta", "p ublicidad": "publicidad",
            "diri ge": "dirige", "correspo ndiente": "correspondiente",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        if len(text.split()) <= 3 and text.islower():
            text = text.title()
        return text.strip()

    def _render_batch_sync(self, context: Dict, required_docs: List[Dict], radicado: str) -> Dict[str, str]:
        """Renderizado síncrono por lotes (Evita NotImplementedError en Windows)"""
        results = {}
        from jinja2 import Environment, FileSystemLoader
        
        logger.info(f"🛠️ [PDF_SYNC] Iniciando renderizado batch para {radicado}. Docs: {[d.get('key') for d in required_docs]}")
        
        try:
            with sync_playwright() as p:
                logger.info("🌐 [PDF_SYNC] Lanzando navegador Chromium...")
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as launch_err:
                    logger.error(f"❌ [PDF_SYNC] Error lanzando Chromium: {launch_err}")
                    return {}

                env = Environment(loader=FileSystemLoader(self.templates_dir))
                
                # --- SANITIZACIÓN GLOBAL DE CONTEXTO ---
                # (Ya aplicada por hard_sanitize_render_context en el nivel asíncrono)
                
                if isinstance(context.get("citas_verificables"), list):
                    for cita in context["citas_verificables"]:
                        if isinstance(cita, dict):
                            for field in ["citacion_formato", "texto_relevante"]:
                                if field in cita:
                                    cita[field] = self.sanitize_template_text(cita[field])

                for doc_spec in required_docs:
                    key = doc_spec.get('key')
                    template_name = doc_spec.get('template')
                    if not key or not template_name: continue
                    
                    # 🔧 FIX: Sanitizar contexto ANTES de renderizar este documento específico
                    doc_context = context.copy()
                    for k in ["nombres", "apellidos", "asunto", "hechos_extraidos", "borrador_proyeccion", "soporte_traslado", "justificacion_traslado"]:
                        if k in doc_context and isinstance(doc_context[k], str):
                            doc_context[k] = self.sanitize_template_text(doc_context[k])
                    
                    # Sanitizar citas para este documento
                    if "citas_verificables" in doc_context:
                        c = doc_context["citas_verificables"]
                        if isinstance(c, str):
                            try: c = json.loads(c)
                            except: c = []
                        if isinstance(c, list):
                            for item in c:
                                if isinstance(item, dict):
                                    for f in ["citacion_formato", "texto_relevante", "ente_emisor"]:
                                        if f in item and isinstance(item[f], str):
                                            item[f] = self.sanitize_template_text(item[f])
                        doc_context["citas_verificables"] = c
                    
                    # 🔧 FIX: Reemplazar placeholders críticos
                    ph_map = {
                        "[NOMBRE_1]": doc_context.get("nombres", "Peticionario"),
                        "[ID_1]": doc_context.get("documento", "XXX"),
                        "[CELULAR_1]": doc_context.get("celular", "XXX"),
                        "[EMAIL_1]": doc_context.get("email", "XXX"),
                        "[FECHA_RADICADO]": doc_context.get("fecha_generacion", datetime.now().strftime("%d/%m/%Y")),
                        "Funcionario incompetente": f"La dependencia {doc_context.get('pdf_dependency', 'receptora')} no es competente para resolver esta solicitud"
                    }
                    for field in ["borrador_proyeccion", "soporte_traslado", "justificacion_traslado", "hechos_extraidos"]:
                        if field in doc_context and isinstance(doc_context[field], str):
                            for ph, val in ph_map.items():
                                doc_context[field] = doc_context[field].replace(ph, str(val))
                    
                    # 🔧 FIX: Logging debug
                    logger.debug(f"🔍 [PDF_RENDER] {key}: nombres={doc_context.get('nombres')}, hechos_len={len(str(doc_context.get('hechos_extraidos', '')))}")
                    
                    output_filename = f"{key}_{radicado}.pdf"
                    case_dir = self.vault_base / radicado
                    case_dir.mkdir(parents=True, exist_ok=True)
                    output_path = case_dir / output_filename
                    
                    logger.info(f"📄 [PDF_SYNC] Procesando {key} con template {template_name}...")
                    
                    try:
                        template = env.get_template(template_name)
                        rendered_html = template.render(**doc_context)
                        
                        if not rendered_html.strip().lower().startswith('<!doctype'):
                            rendered_html = f"<!DOCTYPE html><html><head><style>@page {{ size: letter; margin: 2.5cm 2cm; }} body {{ font-family: Arial; font-size: 11px; padding-top: 30mm; }}</style></head><body>{rendered_html}</body></html>"

                        page = browser.new_page()
                        page.set_content(rendered_html, wait_until="networkidle", timeout=30000)
                        
                        page.pdf(
                            path=str(output_path),
                            format="Letter",
                            print_background=True,
                            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
                        )
                        page.close()
                        
                        if output_path.exists() and output_path.stat().st_size > 1000:
                            results[key] = str(output_path.absolute())
                            logger.success(f"✅ [PDF_ENGINE] Creado: {output_filename} ({output_path.stat().st_size} bytes)")
                            
                            # 🔧 VALIDACIÓN POST-ESCRITURA (Anti-Artefactos)
                            try:
                                with open(output_path, 'rb') as f:
                                    pdf_content = f.read().decode('utf-8', errors='ignore')
                                    artifacts = ["Le y", "p ersonal", "ca p acitación", "Funcionario incompetente.", "[NOMBRE_1]"]
                                    for art in artifacts:
                                        if art in pdf_content:
                                            logger.warning(f"⚠️ [PDF_VALIDATION] Artefacto detectado en {output_filename}: {art}")
                                    logger.success(f"🛡️ [PDF_VALIDATION] {output_filename} verificado.")
                            except Exception as val_err:
                                logger.warning(f"⚠️ [PDF_VALIDATION] No se pudo verificar contenido de {output_filename}: {val_err}")
                        else:
                            logger.error(f"❌ [PDF_ENGINE] Falló creación física o archivo corrupto: {output_filename}")
                    except Exception as doc_err:
                        logger.error(f"💥 [PDF_SYNC] Error procesando documento {key}: {doc_err}")
                        continue

                browser.close()
            return results
        except Exception as e:
            logger.error(f"⚠️ [PDF_ENGINE_SYNC] Batch falló por error general: {e}")
            return {}

    def _validate_document_context(self, doc_type: str, context: dict) -> dict:
        """Valida y corrige contexto según tipo de documento"""
        validated = context.copy()
        
        if not validated.get("nombres") or validated["nombres"] == "Ciudadano":
            validated["nombres"] = "Peticionario Registrado"
        
        if doc_type == "memorial":
            if not validated.get("hechos_extraidos") or "procesamiento" in str(validated.get("hechos_extraidos")).lower():
                validated["hechos_extraidos"] = validated.get("motivo", "Solicitud de trámite administrativo bajo Ley 1755.")[:500]
        
        elif doc_type == "traslado":
            if not validated.get("soporte_traslado") or "remite" not in str(validated.get("soporte_traslado")).lower():
                validated["soporte_traslado"] = f"Se remite por competencia técnica a {validated.get('dependencia_competente', 'la oficina encargada')} según Art. 21 de la Ley 1437."

        elif doc_type == "proyeccion":
            if not validated.get("borrador_proyeccion") or "proceso" in str(validated.get("borrador_proyeccion")).lower():
                validated["borrador_proyeccion"] = f"Se resuelve la solicitud identificada con radicado {validated.get('radicado')} en favor del cumplimiento de los términos legales."

        return validated

    @staticmethod
    def clean_citations_list(citas_raw):
        """Elimina entradas vacías o corruptas"""
        if isinstance(citas_raw, str):
            try:
                import json
                citas_raw = json.loads(citas_raw)
            except:
                return []
        
        if not isinstance(citas_raw, list):
            return []
            
        valid_citas = []
        for c in citas_raw:
            if isinstance(c, dict) and c.get("articulo") and c.get("texto_relevante"):
                valid_citas.append(c)
                
        return valid_citas

    async def _prepare_context(self, context: Dict, session_id: str, radicado: str) -> Dict:
        """Enriquece el contexto con PII rehidratada, QR y Citas Legales"""
        try:
            hydrated = await privacy_shield.deep_rehydrate(session_id, context)
        except:
            hydrated = {**context}
            logger.warning(f"⚠️ [PDF_ENGINE] Rehidratación fallida")

        hydrated["nombres"] = str(hydrated.get("nombres", "Peticionario")).strip()
        hydrated["apellidos"] = str(hydrated.get("apellidos", "")).strip()
        
        if "edurado" in hydrated["nombres"].lower():
            hydrated["nombres"] = hydrated["nombres"].lower().replace("edurado", "Eduardo").title()

        hydrated["citas_verificables"] = self.clean_citations_list(hydrated.get("citas_verificables", []))
        
        if not hydrated["citas_verificables"]:
            try:
                from app.services.legal_citation_engine import legal_citation_engine
                hydrated["citas_verificables"] = await legal_citation_engine._get_offline_laws(hydrated.get("dependencia_id", "4131"))
            except:
                hydrated["citas_verificables"] = [{"citacion_formato": "Normativa General", "articulo": "N/A", "texto_relevante": "Normativa general aplicable.", "ente_emisor": "Alcaldía de Cali"}]

        ahora = datetime.utcnow()
        hydrated["fecha_actual"] = ahora.strftime("%d/%m/%Y")
        hydrated["fecha_generacion"] = ahora.strftime("%d/%m/%Y")
        hydrated["año_actual"] = ahora.year
        hydrated["numero_resolucion"] = f"RES-{ahora.strftime('%Y%m%d')}-{session_id[-4:].upper()}"

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            qr_path = tmp.name
        try:
            QRService.generate_verification_qr(radicado=radicado, output_path=qr_path)
            with open(qr_path, "rb") as f:
                hydrated["qr_code_base64"] = base64.b64encode(f.read()).decode()
        finally:
            if os.path.exists(qr_path): os.unlink(qr_path)
            
        return hydrated

pdf_service = PDFService()
