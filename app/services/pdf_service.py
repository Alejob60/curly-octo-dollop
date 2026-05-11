import os
import json
import base64
import re
import concurrent.futures
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from app.utils.sanitizer import PDFSanitizer
from app.services.pdf_context_builder import prepare_pdf_context
from loguru import logger

class PDFService:
    """
    💎 [V65.12 Diamond] Servicio de Generación de PDFs.
    ✅ Unificado | ✅ Dinámico | ✅ Blindado por Confianza
    """
    def __init__(self):
        self.templates_dir = Path(os.getcwd()) / "templates" / "pdf"
        self.vault_base = Path(os.getcwd()) / "vault_digital"
        self.vault_base.mkdir(parents=True, exist_ok=True)

    def generate(self, context: dict, required_docs: list) -> dict:
        """
        Genera el paquete de documentos oficiales.
        Bloquea si la confianza de la IA es < 0.85 (V65.12).
        """
        import concurrent.futures
        
        # 🛡️ GUARDIA V65.12: Bloqueo por baja confianza
        confidence = float(context.get("confidence", 0.0))
        if confidence < 0.85:
            logger.critical(f"🚫 [PDF_BLOCK] Confianza insuficiente ({confidence:.2f}). Abortando generación.")
            return {}

        def _run_sync_generation():
            # Inyectar contexto base si falta
            full_state = PDFSanitizer.inject_context(context)
            
            # Preparar metadatos para el builder
            metadata = {
                "fecha_solicitada": full_state.get("fecha_confirmada", "No especificada"),
                "fecha_valida": full_state.get("fecha_valida", True),
                "entidad_destino": full_state.get("dependencia_competente", "SECRETARÍA COMPETENTE"),
                "confidence": confidence
            }
            radicado = full_state.get("radicado", "GEN")
            
            # 💎 Transformación Maestra de Contexto (Diamond V65.12)
            from app.services.pdf_context_builder import prepare_pdf_context
            final_context = prepare_pdf_context(full_state, metadata, radicado)
            
            # 🛡️ VALIDACIÓN DE CAMPOS CRÍTICOS (Fase 4)
            critical = ["radicado", "nombre_peticionario", "identificacion", "hechos_extraidos"]
            missing = [k for k in critical if not final_context.get(k)]
            if missing:
                logger.error(f"🚫 [PDF_BLOCKED] Faltan campos críticos: {missing}")
                return {}

            qr_dir = self.vault_base / radicado
            qr_dir.mkdir(parents=True, exist_ok=True)
            
            qr_path = qr_dir / f"qr_{radicado}.png"
            self._generate_qr(radicado, qr_path)
            with open(qr_path, "rb") as f: 
                final_context["qr_code_base64"] = base64.b64encode(f.read()).decode()

            # Forzar versión de app desde env
            final_context["version_engine"] = os.getenv("APP_VERSION", "V65.12")

            results = {}
            env = Environment(loader=FileSystemLoader(str(self.templates_dir)))
            
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    for doc in required_docs:
                        try:
                            key = doc.get("key")
                            template_name = doc.get("template")
                            if not template_name: continue
                            
                            template = env.get_template(template_name)
                            # Renderizado dinámico
                            rendered = template.render(**final_context)
                            
                            pdf_path = qr_dir / f"{key}_{radicado}.pdf"
                            
                            page = browser.new_page()
                            page.set_content(rendered, wait_until="networkidle")
                            page.pdf(
                                path=str(pdf_path), 
                                format="Letter", 
                                margin={"top": "2.5cm", "right": "2cm", "bottom": "2.5cm", "left": "2cm"},
                                print_background=True
                            )
                            page.close()
                            
                            if pdf_path.exists():
                                logger.success(f"✅ [PDF_VALIDATION] {key} verificado. {final_context['version_engine']}")

                            results[key] = str(pdf_path)
                        except Exception as e:
                            logger.error(f"❌ Fallo renderizando {key}: {e}")
                    browser.close()
            except Exception as e:
                logger.error(f"🔥 Fallo crítico en PDF Engine: {e}")
            return results

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_sync_generation)
            return future.result()

    def _generate_qr(self, radicado, path):
        try:
            import qrcode
            qr = qrcode.make(f"http://localhost:8000/verify/{radicado}")
            qr.save(str(path))
        except Exception as e:
            logger.error(f"⚠️ Error generando QR: {e}")

pdf_service = PDFService()
