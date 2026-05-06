import os
import base64
import aiosmtplib
from email.message import EmailMessage
from app.core.config import settings
from loguru import logger
from typing import List

class NotificationService:
    """
    V5.2: Servicio de Notificación Digital Certificada GCP-NATIVE.
    HU 5.1: Envío de Trilogía Documental vía SMTP Relay de GCP.
    Soberanía total: 0 dependencias de Azure.
    """
    
    def __init__(self):
        self.smtp_host = settings.GCP_SMTP_HOST
        self.smtp_port = settings.GCP_SMTP_PORT
        self.smtp_user = settings.GCP_SMTP_USER
        self.smtp_pass = settings.GCP_SMTP_PASS
        self.sender = settings.GCP_EMAIL_SENDER
        logger.info(f"📧 Notification Service (GCP-Relay) configurado en {self.smtp_host}")

    async def send_official_radicado_email(self, recipient_email: str, citizen_name: str, radicado_id: str, pdf_paths: List[str]):
        """
        Envía los 3 documentos oficiales al ciudadano tras la radicación usando SMTP seguro.
        """
        msg = EmailMessage()
        msg["Subject"] = f"Radicación Exitosa: PQRSD No. {radicado_id} - Alcaldía de Cali"
        msg["From"] = self.sender
        msg["To"] = recipient_email
        msg.set_content(f"Estimado(a) {citizen_name}, su radicado {radicado_id} ha sido procesado exitosamente.")

        # Plantilla HTML Institucional
        html_content = f"""
        <html>
            <body style="font-family: sans-serif; color: #1e293b;">
                <div style="max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; background-color: #ffffff;">
                    <h2 style="color: #4f46e5;">Radicación PQRSD Exitosa</h2>
                    <p>Cordial saludo, <b>{citizen_name}</b>.</p>
                    <p>Le informamos que su solicitud ha sido recibida y sellada bajo el número:</p>
                    <div style="background: #f8fafc; padding: 15px; border-radius: 8px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 2px; border: 1px solid #e2e8f0;">
                        #{radicado_id}
                    </div>
                    <p>Adjunto encontrará la <b>Trilogía Documental</b> de su trámite (Memorial, Traslado y Borrador).</p>
                    <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;"/>
                    <p style="font-size: 10px; color: #64748b; text-align: center;">
                        Sello Digital: <b>GCP-IMMUTABLE-WORM</b>. Este radicado es inalterable.
                    </p>
                </div>
            </body>
        </html>
        """
        msg.add_alternative(html_content, subtype="html")

        # Adjuntar Trilogía Documental
        for path in pdf_paths:
            if os.path.exists(path):
                filename = os.path.basename(path)
                with open(path, "rb") as f:
                    file_data = f.read()
                    msg.add_attachment(
                        file_data,
                        maintype="application",
                        subtype="pdf",
                        filename=filename
                    )

        try:
            # Envío asíncrono vía SMTP TLS
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_pass,
                start_tls=True
            )
            logger.success(f"📧 Email certificado enviado vía GCP a {recipient_email}. [Radicado: {radicado_id}]")
            return f"gcp-smtp-{radicado_id}" # ID de rastro local

        except Exception as e:
            logger.error(f"❌ Error enviando email vía GCP-Relay: {e}")
            return None

notification_service = NotificationService()
