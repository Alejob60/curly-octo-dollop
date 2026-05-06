from sqlalchemy import func, select, case, extract
from app.core.db_clients import postgres_manager
from app.models.sql_models import CaseRegistry
import datetime
from loguru import logger

class AnalyticsService:
    """
    SPRINT 4: Motor de Analítica Gubernamental.
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

analytics_service = AnalyticsService()
