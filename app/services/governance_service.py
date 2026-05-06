import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.sql_models import Radicado, Trazabilidad, PqrsType
from loguru import logger

class GovernanceService:
    def calculate_deadline(self, start_date: datetime.datetime, business_days: int) -> datetime.datetime:
        """
        Calcula la fecha de vencimiento sumando días hábiles (Lunes a Viernes).
        Nota: En producción debería considerar festivos de Colombia.
        """
        current_date = start_date
        added_days = 0
        while added_days < business_days:
            current_date += datetime.timedelta(days=1)
            if current_date.weekday() < 5:  # 0-4 son L-V
                added_days += 1
        return current_date

    async def register_radicado(self, session: AsyncSession, data: dict) -> Radicado:
        """
        Registra un nuevo radicado y calcula su reloj de ley.
        """
        # 1. Obtener días de ley para el tipo
        pqrs_type_id = data.get("id_tipo_pqrs")
        result = await session.execute(select(PqrsType).filter_by(id=pqrs_type_id))
        pqrs_type = result.scalars().first()
        
        business_days = pqrs_type.dias_respuesta if pqrs_type else 15
        
        # 2. Calcular vencimiento
        fecha_creacion = datetime.datetime.utcnow()
        fecha_vencimiento = self.calculate_deadline(fecha_creacion, business_days)
        
        # 3. Crear Radicado
        new_radicado = Radicado(
            codigo_radicado=data.get("codigo_radicado"),
            hash_seguridad=data.get("hash_seguridad"),
            fecha_creacion=fecha_creacion,
            fecha_vencimiento=fecha_vencimiento,
            id_usuario_ciudadano=data.get("id_usuario"),
            id_dependencia=data.get("id_dependencia"),
            id_tipo_pqrs=pqrs_type_id,
            estado_actual="RECIBIDO"
        )
        
        session.add(new_radicado)
        await session.flush() # Para obtener el ID
        
        # 4. Registrar trazabilidad inicial
        audit = Trazabilidad(
            radicado_id=new_radicado.id,
            estado_anterior=None,
            estado_nuevo="RECIBIDO",
            comentario="Radicación inicial exitosa vía Orbital Prime Engine."
        )
        session.add(audit)
        
        return new_radicado

    def get_orfeo_metadata(self, fecha_creacion: datetime.datetime, dias_respuesta: int) -> dict:
        """
        QUAL-01: Genera los metadatos al estilo Orfeo para el Dashboard.
        Calcula cuántos días hábiles han pasado desde la radicación.
        """
        try:
            ahora = datetime.datetime.utcnow()
            dias_pasados = 0
            temp_date = fecha_creacion
            
            while temp_date < ahora:
                temp_date += datetime.timedelta(days=1)
                if temp_date.weekday() < 5: # Solo L-V
                    dias_pasados += 1
            
            return {
                "dias_tramite_label": f"{dias_pasados} de {dias_respuesta}",
                "porcentaje_vencimiento": round((dias_pasados / dias_respuesta) * 100, 2),
                "is_expired": dias_pasados > dias_respuesta
            }
        except Exception as e:
            logger.error(f"Error en metadatos Orfeo: {e}")
            return {"dias_tramite_label": "0 de 0", "porcentaje_vencimiento": 0}

governance_service = GovernanceService()
