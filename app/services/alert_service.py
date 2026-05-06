import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.sql_models import Radicado, User, Trazabilidad
from app.services.notification_service import notification_service
from loguru import logger

class AlertService:
    async def check_deadlines_and_alert(self, session: AsyncSession):
        """
        ALERT-01: Proceso de Auditoría de Vencimientos.
        Identifica casos en riesgo de mora y escala a los Secretarios.
        """
        logger.info("🕒 Iniciando escaneo de vencimientos legales...")
        
        ahora = datetime.datetime.utcnow()
        # Buscamos radicados abiertos cuya fecha de vencimiento sea en < 48 horas
        threshold = ahora + datetime.timedelta(hours=48)
        
        query = select(Radicado, User.full_name, User.email, User.id_dependencia)\
            .join(User, Radicado.id_funcionario_asignado == User.id)\
            .filter(Radicado.estado_actual.in_(["ASIGNADO", "PENDIENTE_VISTO_BUENO"]))\
            .filter(Radicado.fecha_vencimiento <= threshold)
            
        result = await session.execute(query)
        risky_cases = result.all()
        
        for rad, func_name, func_email, dep_id in risky_cases:
            # 1. Alerta Nivel 1: Al Funcionario Responsable (NOT-05)
            logger.warning(f"🚨 Alerta de Vencimiento: Radicado {rad.codigo_radicado} vence el {rad.fecha_vencimiento}")
            
            await notification_service.send_internal_alert(
                recipient_email=func_email,
                message=f"¡Atención {func_name}! El radicado {rad.codigo_radicado} vence en menos de 48 horas. Requiere acción inmediata."
            )
            
            # 2. Alerta Nivel 2: Escalamiento al Jefe de Dependencia (ALERT-01)
            # Buscamos al Secretario de la oficina
            boss_query = select(User).filter_by(id_dependencia=dep_id, role_id=4) # Role 4 = Secretario
            boss_res = await session.execute(boss_query)
            boss = boss_res.scalars().first()
            
            if boss:
                await notification_service.send_internal_alert(
                    recipient_email=boss.email,
                    message=f"🚩 ALERTA DE GERENCIA: Su equipo tiene un radicado ({rad.codigo_radicado}) en riesgo de silencio administrativo."
                )

        return len(risky_cases)

alert_service = AlertService()
