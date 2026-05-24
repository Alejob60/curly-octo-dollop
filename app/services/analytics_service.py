from sqlalchemy import func, select, case, extract
from app.core.db_clients import postgres_manager
from app.models.sql_models import CaseRegistry
import datetime
from loguru import logger

class AnalyticsService:
    """
    SPRINT 4: Motor de Analítica Gubernamental con Integración Cali-Lex V65.6.
    Calcula métricas de eficiencia, calidad y cumplimiento normativo.
    """

    async def get_dashboard_metrics(self) -> dict:
        """
        Calcula KPIs en tiempo real desde PostgreSQL.
        Métricas: SLA, Grounding Ratio, Tasa de Revisión, Casos por Dependencia.
        """
        async with postgres_manager.get_session() as session:
            try:
                # 1. Total casos y distribución por estado
                stmt_status = select(CaseRegistry.estado, func.count(CaseRegistry.id)).group_by(CaseRegistry.estado)
                res_status = await session.execute(stmt_status)
                status_dist = {row[0]: row[1] for row in res_status.all()}

                # 2. SLA Promedio (en días) para casos FIRMADOS
                # Calculamos la diferencia entre created_at y updated_at (cuando se firma)
                stmt_sla = select(func.avg(extract('epoch', CaseRegistry.updated_at - CaseRegistry.created_at) / 86400)).where(CaseRegistry.estado == "FIRMADO")
                res_sla = await session.execute(stmt_sla)
                avg_sla = res_sla.scalar() or 0.0

                # 3. Grounding Ratio Promedio (Calidad de la base legal)
                stmt_grounding = select(func.avg(CaseRegistry.grounding_score)).where(CaseRegistry.grounding_score > 0)
                res_grounding = await session.execute(stmt_grounding)
                avg_grounding = res_grounding.scalar() or 0.0

                # 4. Review Score Promedio (Calidad IA)
                stmt_review = select(func.avg(CaseRegistry.review_score)).where(CaseRegistry.review_score > 0)
                res_review = await session.execute(stmt_review)
                avg_review = res_review.scalar() or 0.0

                # 5. Casos por Dependencia
                stmt_deps = select(CaseRegistry.dependencia_nombre, func.count(CaseRegistry.id)).group_by(CaseRegistry.dependencia_nombre)
                res_deps = await session.execute(stmt_deps)
                deps_dist = {row[0]: row[1] for row in res_deps.all() if row[0]}

                return {
                    "total_cases": sum(status_dist.values()),
                    "by_status": status_dist,
                    "avg_sla_days": round(float(avg_sla), 2),
                    "avg_grounding_score": round(float(avg_grounding), 2),
                    "avg_review_score": round(float(avg_review), 2),
                    "by_dependency": deps_dist,
                    "last_updated": datetime.datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"❌ Error calculando métricas de analítica: {e}")
                return {"error": str(e)}

    async def get_calilex_metrics(self, days: int = 7) -> dict:
        """
        Obtiene métricas específicas del agente Cali-Lex Advisor V65.6 desde PostgreSQL.
        Incluye análisis de confianza, bloqueo de PDFs y distribución de complejidad.
        """
        async with postgres_manager.get_session() as session:
            try:
                cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
                
                # 1. Total casos analizados por Calilex
                stmt_total = select(func.count(CaseRegistry.id)).where(
                    CaseRegistry.created_at >= cutoff,
                    CaseRegistry.confidence_score > 0
                )
                result = await session.execute(stmt_total)
                total_analyzed = result.scalar() or 0
                
                # 2. Promedios de scores Calilex
                stmt_scores = select(
                    func.avg(CaseRegistry.confidence_score),
                    func.avg(CaseRegistry.grounding_score),
                    func.avg(CaseRegistry.completeness_score)
                ).where(
                    CaseRegistry.created_at >= cutoff,
                    CaseRegistry.confidence_score > 0
                )
                result = await session.execute(stmt_scores)
                row = result.one()
                avg_confidence = float(row[0] or 0)
                avg_grounding = float(row[1] or 0)
                avg_completeness = float(row[2] or 0)
                
                # 3. Casos bloqueados para PDF (confianza < 0.85)
                stmt_blocked = select(func.count(CaseRegistry.id)).where(
                    CaseRegistry.created_at >= cutoff,
                    CaseRegistry.confidence_score < 0.85
                )
                result = await session.execute(stmt_blocked)
                blocked_count = result.scalar() or 0
                
                # 4. Casos que requieren revisión humana
                stmt_human_review = select(func.count(CaseRegistry.id)).where(
                    CaseRegistry.created_at >= cutoff,
                    CaseRegistry.human_review_required == True
                )
                result = await session.execute(stmt_human_review)
                human_review_count = result.scalar() or 0
                
                # 5. Distribución por nivel de complejidad
                stmt_complexity = select(
                    CaseRegistry.complexity_level,
                    func.count(CaseRegistry.id)
                ).where(
                    CaseRegistry.created_at >= cutoff,
                    CaseRegistry.complexity_level != None
                ).group_by(CaseRegistry.complexity_level)
                result = await session.execute(stmt_complexity)
                complexity_dist = {row[0]: row[1] for row in result.all() if row[0]}
                
                # 6. Alertas de fecha inválida
                stmt_date_alerts = select(func.count(CaseRegistry.id)).where(
                    CaseRegistry.created_at >= cutoff,
                    CaseRegistry.fecha_alert != None
                )
                result = await session.execute(stmt_date_alerts)
                date_alert_count = result.scalar() or 0
                
                return {
                    "total_analyzed_by_calilex": total_analyzed,
                    "avg_confidence_score": round(avg_confidence, 3),
                    "avg_grounding_by_calilex": round(avg_grounding, 3),
                    "avg_completeness_score": round(avg_completeness, 3),
                    "pdf_blocked_count": blocked_count,
                    "pdf_block_rate": round(blocked_count / max(total_analyzed, 1), 3),
                    "human_review_required": human_review_count,
                    "human_review_rate": round(human_review_count / max(total_analyzed, 1), 3),
                    "complexity_distribution": complexity_dist,
                    "date_alerts": date_alert_count,
                    "calilex_version": "V65.6",
                    "period_days": days,
                    "last_updated": datetime.datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"❌ Calilex metrics error: {e}")
                return {"error": str(e)}

analytics_service = AnalyticsService()
