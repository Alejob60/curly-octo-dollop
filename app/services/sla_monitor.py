import datetime
from sqlalchemy import select, update
from app.core.db_clients import postgres_manager
from app.models.sql_models import CaseRegistry
from loguru import logger

class SLAMonitor:
    """
    SPRINT 1.2 (GovTech PR-01): Motor de Prevención de Silencio Administrativo.
    Monitorea los términos legales y dispara alertas proactivas.
    """
    async def audit_legal_deadlines(self):
        """Revisa todos los casos abiertos y actualiza su semáforo de urgencia."""
        logger.info("⏱️ [SLA_MONITOR] Iniciando auditoría de términos legales...")
        
        async with postgres_manager.get_session() as session:
            # 1. Buscar casos no finalizados
            stmt = select(CaseRegistry).where(CaseRegistry.estado.in_(["INICIADO", "ANALIZADO", "REVISADO", "EN_COLA"]))
            result = await session.execute(stmt)
            cases = result.scalars().all()
            
            now = datetime.datetime.utcnow()
            updates = 0

            for case in cases:
                if not case.vencimiento_legal:
                    # Si no tiene fecha, la calculamos (15 días desde creación)
                    case.vencimiento_legal = case.created_at + datetime.timedelta(days=15)
                
                diff = case.vencimiento_legal - now
                hours_left = diff.total_seconds() / 3600
                
                old_alert = case.alerta_vencimiento
                
                # 2. Lógica de Semáforo GovTech
                if hours_left <= 0:
                    case.alerta_vencimiento = "CRISIS" # SILENCIO ADMINISTRATIVO
                elif hours_left <= 24:
                    case.alerta_vencimiento = "RED"    # INMINENTE
                elif hours_left <= 72:
                    case.alerta_vencimiento = "YELLOW" # PREVENTIVA
                else:
                    case.alerta_vencimiento = "VERDE"  # SEGURO

                if old_alert != case.alerta_vencimiento:
                    updates += 1
                    logger.warning(f"🚨 [SLA_ALERT] Caso {case.radicado} cambió a {case.alerta_vencimiento} ({hours_left:.1f}h restantes)")
            
            await session.commit()
            logger.success(f"✅ [SLA_MONITOR] Auditoría completada. {updates} casos actualizados.")

sla_monitor = SLAMonitor()
