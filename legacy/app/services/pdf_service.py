import os
import json
import base64
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from app.utils.text_sanitizer import validate_and_clean_context
from loguru import logger

class PDFService:
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent.parent / "templates" / "pdf"
        self.vault_base = Path.cwd() / "vault_digital"
        self.vault_base.mkdir(parents=True, exist_ok=True)

    def generate(self, context: dict, required_docs: list) -> dict:
        """
        Generación DIRECTA y SÍNCRONA de PDFs (V65.0 Bulletproof)
        """
        # 1. SANITIZACIÓN OBLIGATORIA ANTES DE CUALQUIER COSA
        context = validate_and_clean_context(context)
        
        radicado = context.get("radicado", "GEN")
        qr_dir = self.vault_base / radicado
        qr_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. QR Generation
        qr_path = qr_dir / f"qr_{radicado}.png"
        self._generate_qr(radicado, qr_path)
        with open(qr_path, "rb") as f: 
            context["qr_code_base64"] = base64.b64encode(f.read()).decode()

        results = {}
        env = Environment(loader=FileSystemLoader(self.templates_dir))
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                for doc in required_docs:
                    try:
                        key = doc.get("key")
                        template_name = doc.get("template")
                        if not template_name: continue
                        
                        template = env.get_template(template_name)
                        html = template.render(**context)
                        pdf_path = qr_dir / f"{key}_{radicado}.pdf"
                        
                        page = browser.new_page()
                        # Configuración optimizada para Windows
                        page.set_content(html, wait_until="networkidle")
                        page.pdf(
                            path=str(pdf_path), 
                            format="Letter", 
                            margin={"top": "2.5cm", "right": "2cm", "bottom": "2.5cm", "left": "2cm"},
                            print_background=True
                        )
                        page.close()
                        results[key] = str(pdf_path)
                        logger.success(f"✅ PDF Generado: {key}")
                    except Exception as e:
                        logger.error(f"❌ Fallo renderizando {doc.get('key')}: {e}")
                browser.close()
        except Exception as e:
            logger.error(f"🔥 Fallo crítico en PDF Engine: {e}")
            
        return results

    def _generate_qr(self, radicado, path):
        """Generador de QR integrado"""
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(f"http://localhost:8000/verify/{radicado}")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(str(path))
        except Exception as e:
            logger.error(f"⚠️ Error generando QR: {e}")

pdf_service = PDFService()
