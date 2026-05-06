from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.models.sql_models import User, Radicado, Trazabilidad
from loguru import logger
import datetime

class AssignmentService:
    async def assign_to_best_official(self, session: AsyncSession, radicado_id: int, dependency_id: int, topic: str = None) -> int:
        """
        LOGIC-02: Algoritmo de reparto por afinidad semántica y carga mínima.
        Prioriza expertos en el tema antes de buscar por carga general.
        """
        try:
            # 1. Intentar buscar por especialidad (Afinidad Semántica)
            expert_official = None
            if topic:
                expert_query = select(User).filter(
                    User.id_dependencia == dependency_id,
                    User.is_available == True,
                    User.especialidad.ilike(f"%{topic}%")
                ).order_by(User.carga_actual.asc())
                
                expert_result = await session.execute(expert_query)
                expert_official = expert_result.scalars().first()

            # 2. Si no hay experto, buscar por carga mínima general en la dependencia
            if not expert_official:
                general_query = select(User).filter(
                    User.id_dependencia == dependency_id,
                    User.is_available == True
                ).order_by(User.carga_actual.asc())
                
                general_result = await session.execute(general_query)
                expert_official = general_result.scalars().first()
            
            if not expert_official:
                logger.warning(f"🚨 Alerta de Despacho: No hay funcionarios disponibles en la dependencia {dependency_id}.")
                return None
            
            # 3. Ejecutar la asignación
            rad_query = select(Radicado).filter_by(id=radicado_id)
            rad_result = await session.execute(rad_query)
            radicado = rad_result.scalars().first()
            
            if radicado:
                radicado.id_funcionario_asignado = expert_official.id
                radicado.estado_actual = "ASIGNADO"
                expert_official.carga_actual += 1
                
                # Registro de Trazabilidad con justificación de asignación
                razon = f"Afinidad semántica: {topic}" if topic and expert_official.especialidad else "Carga mínima general"
                audit = Trazabilidad(
                    radicado_id=radicado.id,
                    estado_anterior="RECIBIDO",
                    estado_nuevo="ASIGNADO",
                    id_funcionario=str(expert_official.id),
                    comentario=f"Asignación inteligente Orbital Prime. Motivo: {razon}."
                )
                session.add(audit)
                
                logger.info(f"⚖️ Radicado {radicado.codigo_radicado} asignado a {expert_official.full_name} ({razon})")
                return expert_official.id
                
        except Exception as e:
            logger.error(f"Error en Dynamic Load Balancer: {e}")
            return None

assignment_service = AssignmentService()
