"""
Servicio para generación de códigos QR con validación segura
"""

import qrcode
import hashlib
from pathlib import Path
from app.core.config import settings
from loguru import logger

class QRService:
    BASE_VERIFY_URL = settings.VERIFY_BASE_URL  # ej: "http://localhost:8000/verify"
    
    @staticmethod
    def generate_verification_qr(radicado: str, output_path: str, size: int = 150):
        """
        Genera QR para verificación pública con hash de validación.
        """
        # Generar hash seguro para el QR (previene enumeración)
        hash_value = hashlib.sha256(radicado.encode()).hexdigest()
        
        # Construir URL pública (para el demo usamos hash completo o truncado, verify.py usará el mismo)
        verify_url = f"{QRService.BASE_VERIFY_URL}/{radicado}?hash={hash_value}"
        
        # Asegurar que el directorio existe
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Generar QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(verify_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)
        logger.info(f"📱 [QR_SERVICE] QR generado en {output_path} -> {verify_url}")
        
        return output_path
    
    @staticmethod
    def get_qr_position(template_type: str) -> dict:
        """
        Retorna coordenadas para posicionar QR en parte superior derecha del PDF.
        Coordenadas en mm desde la esquina superior derecha.
        """
        positions = {
            "memorial": {"right_margin": 15, "top_margin": 15, "size": 20},
            "traslado": {"right_margin": 15, "top_margin": 15, "size": 20},
            "proyeccion": {"right_margin": 15, "top_margin": 15, "size": 20},
        }
        return positions.get(template_type, positions["memorial"])

qr_service = QRService()
