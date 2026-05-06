import os
import base64
from loguru import logger
from google.oauth2 import service_account
from googleapiclient.discovery import build
from email.mime.text import MIMEText

class GoogleWorkspaceBridge:
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/gmail.send'
        ]
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.creds = None
        if self.creds_path and os.path.exists(self.creds_path):
            self.creds = service_account.Credentials.from_service_account_file(
                self.creds_path, scopes=self.scopes
            )
            logger.success("✅ Conexión con Google Workspace establecida vía Service Account.")
        else:
            logger.warning("⚠️ Credenciales de Google no encontradas. Operando en modo local.")

    def send_official_email(self, to_email: str, subject: str, body: str):
        """Dispara un correo real desde la cuenta institucional."""
        if not self.creds: return False
        try:
            service = build('gmail', 'v1', credentials=self.creds)
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(userId='me', body={'raw': raw}).execute()
            logger.info(f"📧 Notificación enviada exitosamente a {to_email}")
            return True
        except Exception as e:
            logger.error(f"Error enviando Gmail: {e}")
            return False

    def create_calendar_events(self, calendar_id: str, events: list):
        """Inyecta los hitos del radicado en el calendario oficial."""
        if not self.creds: return False
        try:
            service = build('calendar', 'v3', credentials=self.creds)
            for ev in events:
                event_body = {
                    'summary': ev['summary'],
                    'description': ev['description'],
                    'start': {'dateTime': ev['start'], 'timeZone': 'America/Bogota'},
                    'end': {'dateTime': ev['start'], 'timeZone': 'America/Bogota'},
                }
                service.events().insert(calendarId=calendar_id, body=event_body).execute()
            logger.info(f"📅 {len(events)} hitos agendados en el calendario de la dependencia.")
            return True
        except Exception as e:
            logger.error(f"Error inyectando Calendar: {e}")
            return False

google_bridge = GoogleWorkspaceBridge()
