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
            
            # 2. Ejecutar renderizado en un ThreadPool para no bloquear el event loop
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

    def _render_batch_sync(self, context: Dict, required_docs: List[Dict], radicado: str) -> Dict[str, str]:
        """Renderizado síncrono por lotes (Evita NotImplementedError en Windows)"""
        results = {}
        from jinja2 import Environment, FileSystemLoader
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                env = Environment(loader=FileSystemLoader(self.templates_dir))
                
                for doc_spec in required_docs:
                    key = doc_spec.get('key')
                    template_name = doc_spec.get('template')
                    if not key or not template_name: continue
                    
                    output_filename = f"{key}_{radicado}.pdf"
                    case_dir = self.vault_base / radicado
                    case_dir.mkdir(parents=True, exist_ok=True)
                    output_path = case_dir / output_filename
                    
                    # Renderizar HTML
                    template = env.get_template(template_name)
                    html = template.render(**context)
                    
                    if not html.strip().lower().startswith('<!doctype'):
                        html = f"<!DOCTYPE html><html><head><style>@page {{ size: letter; margin: 2.5cm 2cm; }} body {{ font-family: Arial; font-size: 11px; padding-top: 30mm; }}</style></head><body>{html}</body></html>"

                    # Generar PDF
                    page = browser.new_page()
                    page.set_content(html, wait_until="networkidle")
                    page.pdf(
                        path=str(output_path),
                        format="Letter",
                        print_background=True,
                        margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
                    )
                    page.close()
                    
                    if output_path.exists() and output_path.stat().st_size > 1000:
                        results[key] = str(output_path.absolute())
                        logger.success(f"✅ [PDF_ENGINE] Creado: {output_filename}")
                    else:
                        logger.error(f"❌ [PDF_ENGINE] Falló creación física: {output_filename}")

                browser.close()
            return results
        except Exception as e:
            logger.error(f"⚠️ [PDF_ENGINE_SYNC] Batch falló: {e}")
            return {}

    async def _prepare_context(self, context: Dict, session_id: str, radicado: str) -> Dict:
        """Enriquece el contexto con PII rehidratada y QR en Base64"""
        try:
            hydrated = await privacy_shield.deep_rehydrate(session_id, context)
        except:
            hydrated = {**context}
            logger.warning(f"⚠️ [PDF_ENGINE] Rehidratación fallida")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            qr_path = tmp.name
        try:
            QRService.generate_verification_qr(radicado=radicado, output_path=qr_path)
            with open(qr_path, "rb") as f:
                hydrated["qr_code_base64"] = base64.b64encode(f.read()).decode()
        finally:
            if os.path.exists(qr_path): os.unlink(qr_path)
            
        hydrated.setdefault("fecha_generacion", datetime.now().strftime("%d/%m/%Y"))
        return hydrated

pdf_service = PDFService()
