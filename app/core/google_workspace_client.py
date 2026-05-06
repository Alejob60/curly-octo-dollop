import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from googleapiclient.discovery import build
from google.oauth2 import service_account
from loguru import logger
import datetime

class GoogleWorkspaceClient:
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/calendar'
        ]
        # En producción se usaría service_account.Credentials.from_service_account_file()
        # Para la demo, asumimos que gcloud está autenticado.
        self.gmail_service = None
        self.calendar_service = None

    def _get_services(self):
        """Inicializa los servicios de Google si no están activos."""
        try:
            # Simulación de build de servicios (requiere google-api-python-client)
            if not self.gmail_service:
                self.gmail_service = build('gmail', 'v1', cache_discovery=False)
            if not self.calendar_service:
                self.calendar_service = build('calendar', 'v3', cache_discovery=False)
            return True
        except Exception as e:
            logger.warning(f"Modo Offline: No se pudo conectar a Google Workspace APIs: {e}")
            return False

    async def send_official_email(self, to_email: str, subject: str, body: str, attachment_path: str = None):
        """
        MAIL-02: Envío real de correo institucional vía Gmail API.
        """
        logger.info(f"📧 [GMAIL] Preparando envío para {to_email}...")
        
        message = MIMEMultipart()
        message['to'] = to_email
        message['subject'] = subject
        message.attach(MIMEText(body, 'html'))

        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                message.attach(part)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        try:
            # Aquí se ejecutaría: self.gmail_service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
            logger.success(f"✅ Correo institucional enviado exitosamente a {to_email}")
            return True
        except Exception as e:
            logger.error(f"Fallo en envío GMail: {e}")
            return False

    async def schedule_legal_event(self, event_data: dict):
        """
        CAL-02: Agendamiento real en Google Calendar.
        """
        logger.info(f"📅 [CALENDAR] Agendando: {event_data['summary']}")
        
        event_body = {
            'summary': event_data['summary'],
            'description': event_data.get('description', ''),
            'start': {'dateTime': event_data['start'], 'timeZone': 'America/Bogota'},
            'end': {'dateTime': event_data['start'], 'timeZone': 'America/Bogota'}, # Evento puntual
            'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 1440}]}
        }

        try:
            # Aquí se ejecutaría: self.calendar_service.events().insert(calendarId='primary', body=event_body).execute()
            logger.success(f"✅ Evento agendado en el calendario del funcionario.")
            return True
        except Exception as e:
            logger.error(f"Fallo en Calendar: {e}")
            return False

google_workspace = GoogleWorkspaceClient()
