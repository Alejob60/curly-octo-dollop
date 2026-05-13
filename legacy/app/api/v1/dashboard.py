from fastapi import APIRouter, HTTPException, Depends
from typing import List, Any
from app.services.analytics_service import analytics_service
from app.services.persistence_bridge import persistence_bridge
from app.core.db_clients import postgres_manager
from app.models.sql_models import CaseRegistry
from sqlalchemy import select, desc
from loguru import logger

router = APIRouter()

@router.get("/analytics")
async def get_governance_analytics():
    """
    SPRINT 4: Recupera KPIs de gestión PQRSD para el Dashboard.
    """
    metrics = await analytics_service.get_dashboard_metrics()
    if "error" in metrics:
        raise HTTPException(status_code=500, detail=metrics["error"])
    return metrics

@router.get("/analytics/calilex")
async def get_calilex_analytics(days: int = 7):
    """
    Métricas específicas del agente Cali-Lex Advisor V65.6 para analítica PQRS.
    
    Incluye:
    - Total casos analizados por Calilex
    - Scores promedio (confianza, grounding, completitud)
    - Tasa de bloqueo de PDFs (confianza < 0.85)
    - Casos que requieren revisión humana
    - Distribución por complejidad
    - Alertas de fecha inválida
    
    Parámetro opcional:
    - days: Rango de días para el análisis (default: 7)
    """
    metrics = await analytics_service.get_calilex_metrics(days)
    if "error" in metrics:
        raise HTTPException(status_code=500, detail=metrics["error"])
    return metrics

@router.get("/cases")
async def get_governance_cases(limit: int = 50, offset: int = 0):
    """
    SPRINT 1: Listado de casos desde la fuente de verdad (PostgreSQL).
    Sustituye la consulta a Valkey por una consulta persistente.
    """
    async with postgres_manager.get_session() as session:
        try:
            stmt = select(CaseRegistry).order_by(desc(CaseRegistry.created_at)).offset(offset).limit(limit)
            result = await session.execute(stmt)
            records = result.scalars().all()
            
            cases = []
            for r in records:
                cases.append({
                    "id": r.radicado,
                    "session_id": r.session_id,
                    "asunto": r.asunto or "En clasificación...",
                    "fecha": r.created_at.isoformat(),
                    "dependencia": r.dependencia_nombre or "GENERAL",
                    "estado": r.estado,
                    "fase": r.current_phase,
                    "score_ia": r.review_score,
                    "urgencia": r.urgencia_flag
                })
            return {"status": "success", "count": len(cases), "cases": cases}
        except Exception as e:
            logger.error(f"❌ Error listando casos desde DB: {e}")
            raise HTTPException(status_code=500, detail="Error al recuperar expedientes")

@router.get("/cases/{radicado}")
async def get_case_detail(radicado: str):
    """Recupera el dossier completo de un caso para inspección forense."""
    async with postgres_manager.get_session() as session:
        stmt = select(CaseRegistry).where(CaseRegistry.radicado == radicado)
        result = await session.execute(stmt)
        r = result.scalar_one_or_none()
        
        if not r:
            raise HTTPException(status_code=404, detail="Radicado no encontrado")
            
        return {c.name: getattr(r, c.name) for c in r.__table__.columns}
