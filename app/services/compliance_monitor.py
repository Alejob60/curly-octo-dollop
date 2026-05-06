from sqlalchemy import select, update, and_
from app.core.db_clients import postgres_manager
from app.models.sql_models import CaseRegistry, AuditLedger
from datetime import datetime, timedelta
from loguru import logger
import json

class AutonomousComplianceMonitor:
    """
    V60.1: Monitor Autónomo de Cumplimiento y SLA.
    Rastrea vencimientos y escala automáticamente casos críticos.
    """

    async def check_sla_breaches(self):
        """
        Analiza todos los casos activos y detecta proximidad a vencimiento legal.
        Escalación: Si faltan < 24h, marca como URGENCIA_CRITICA.
        """
        async with postgres_manager.get_session() as session:
            try:
                now = datetime.utcnow()
                limit_24h = now + timedelta(hours=24)

                # 1. Buscar casos próximos a vencer (menos de 24 horas)
                stmt = select(CaseRegistry).where(
                    and_(
                        CaseRegistry.estado.in_(["PENDIENTE_MAESTRA", "EN_REVISION_DEPENDENCIA"]),
                        CaseRegistry.vencimiento_legal <= limit_24h,
                        CaseRegistry.urgencia_flag != "CRITICA"
                    )
                )
                
                result = await session.execute(stmt)
                critical_cases = result.scalars().all()

                for case in critical_cases:
                    logger.warning(f"🚨 [SLA_BREACH] Radicado {case.radicado} a punto de vencer. Escalando...")
                    
                    # Escalación Automática
                    case.urgencia_flag = "CRITICA"
                    case.updated_at = now
                    
                    # Registro en Ledger de Escalación
                    log = AuditLedger(
                        registry_id=case.radicado,
                        action="AUTOMATIC_SLA_ESCALATION",
                        payload={
                            "reason": "Vencimiento en menos de 24 horas",
                            "deadline": case.vencimiento_legal.isoformat()
                        },
                        created_at=now
                    )
                    session.add(log)

                await session.commit()
                return {"checked": len(critical_cases), "escalated": len(critical_cases)}

            except Exception as e:
                logger.error(f"❌ Error en Compliance Monitor: {e}")
                await session.rollback()
                return {"error": str(e)}

    async def get_metrics(self):
        """
        Recupera KPIs de cumplimiento para Prometheus/Dashboard.
        """
        async with postgres_manager.get_session() as session:
            from sqlalchemy import func
            
            total_stmt = select(func.count(CaseRegistry.id))
            breached_stmt = select(func.count(CaseRegistry.id)).where(CaseRegistry.vencimiento_legal < datetime.utcnow())
            
            total = await session.execute(total_stmt)
            breached = await session.execute(breached_stmt)
            
            return {
                "total_cases": total.scalar(),
                "sla_breach_count": breached.scalar(),
                "compliance_ratio": (total.scalar() - breached.scalar()) / total.scalar() if total.scalar() > 0 else 1.0
            }

compliance_monitor = AutonomousComplianceMonitor()
