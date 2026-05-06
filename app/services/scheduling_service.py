import datetime
from loguru import logger

class SchedulingService:
    def create_calendar_payload(self, radicado_id: str, start_date: datetime.datetime, business_days: int) -> dict:
        """
        CAL-03: Smart Scheduling v2 - Agendamiento de 4 hitos para Google Calendar (T+0, T+7, T+14, T+15).
        """
        try:
            from app.services.governance_service import governance_service

            # Hitos legales asumiendo 15 días hábiles para petición general
            t_7 = governance_service.calculate_deadline(start_date, int(business_days/2)) if business_days > 7 else governance_service.calculate_deadline(start_date, 1)
            t_14 = governance_service.calculate_deadline(start_date, business_days - 1) if business_days > 1 else governance_service.calculate_deadline(start_date, business_days)
            deadline = governance_service.calculate_deadline(start_date, business_days)

            events = [
                {
                    "summary": f"🚩 T+0 INICIO: Radicado {radicado_id}",
                    "start": start_date.isoformat(),
                    "description": "Radicado ingresado y asignado."
                },
                {
                    "summary": f"⚠️ T+7 CONTROL MEDIO: Radicado {radicado_id}",
                    "start": t_7.isoformat(),
                    "description": "Punto de control a mitad de término legal."
                },
                {
                    "summary": f"🚨 T+14 ALERTA CRÍTICA: Radicado {radicado_id}",
                    "start": t_14.isoformat(),
                    "description": "Falta 1 día para vencimiento legal. Escalamiento inminente."
                },
                {
                    "summary": f"🛑 T+15 VENCIMIENTO: Radicado {radicado_id}",
                    "start": deadline.isoformat(),
                    "description": "FECHA LÍMITE LEGAL - LEY 1755."
                }
            ]

            from app.bridge.google_bridge import google_bridge

            calendar_id = "primary" # En prod sería el ID del calendario de la dependencia
            google_bridge.create_calendar_events(calendar_id, events)

            logger.success(f"Misión Cumplida: Cronograma v2 de 4 hitos inyectado en Google Workspace para {radicado_id}")
            return {"radicado_id": radicado_id, "events": events}
        except Exception as e:
            logger.error(f"Error en Smart Scheduling: {e}")
            return None

scheduling_service = SchedulingService()
