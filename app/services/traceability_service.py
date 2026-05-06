import hashlib
import qrcode
import uuid
import datetime
from loguru import logger
import os

class TraceabilityService:
    def generate_radicado_code(self) -> str:
        """WOW-01: Genera un radicado único siguiendo el estándar alfanumérico."""
        year = datetime.datetime.now().year
        unique_id = uuid.uuid4().hex[:6].upper()
        return f"CALI-{year}-{unique_id}"

    def generate_security_hash(self, citizen_id: str, content: str) -> str:
        """WOW-02: Sello Digital SHA-256 (Cédula + Texto + Timestamp)."""
        timestamp = datetime.datetime.now().isoformat()
        payload = f"{citizen_id}|{content}|{timestamp}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def generate_qr_tracking(self, radicado: str, hash_ledger: str) -> str:
        """WOW-03: Generador de Código QR que apunta al portal público de seguimiento."""
        tracking_url = f"https://orbitalprime.com.co/track/{radicado}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(tracking_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Guardar QR en carpeta local del proyecto
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        target_dir = os.path.join(base_dir, "temp_docs")
        os.makedirs(target_dir, exist_ok=True)
        
        qr_path = os.path.join(target_dir, f"qr_{radicado}.png")
        img.save(qr_path)
        
        logger.info(f"QR generado exitosamente para radicado {radicado}")
        return qr_path

traceability_service = TraceabilityService()
