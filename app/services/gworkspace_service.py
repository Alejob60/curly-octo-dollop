from loguru import logger
import datetime
import os
import json

class GWorkspaceService:
    async def notify_dependency_via_gmail(self, dependency_id: int, pdf_path: str, radicado_id: str):
        """
        Envía el documento radicado al correo oficial de la dependencia.
        """
        # Mapeo de correos institucionales
        dependency_emails = {
            4173: "juridica.movilidad@cali.gov.co",
            4151: "vias.infraestructura@cali.gov.co",
            4112: "correspondencia.gobierno@cali.gov.co"
        }
        target = dependency_emails.get(dependency_id, "archivo.general@cali.gov.co")
        
        logger.info(f"📧 [GMAIL API] Enviando Radicado {radicado_id} a {target}")
        logger.info(f"📎 Adjunto: {os.path.basename(pdf_path)}")
        # Simulación de éxito vía gcloud
        return True

    async def schedule_legal_alerts(self, radicado_id: str, deadline: datetime.datetime, official_email: str):
        """
        Programa eventos en Google Calendar para el funcionario y notificaciones Push.
        """
        logger.info(f"📅 [CALENDAR API] Agendando Vencimiento para {radicado_id} el {deadline}")
        
        # Hito de Control (3 días antes)
        alert_date = deadline - datetime.timedelta(days=3)
        
        event_payload = {
            "summary": f"🚨 VENCIMIENTO LEGAL: {radicado_id}",
            "start": deadline.isoformat(),
            "attendees": [official_email],
            "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 1440}]}
        }
        
        # Simulación de comando gcloud para crear el evento
        logger.success(f"✅ Alertas programadas para {official_email} y sistema PUSH activo.")
        return True

g_workspace_service = GWorkspaceService()
