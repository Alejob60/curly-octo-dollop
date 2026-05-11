from fastapi import APIRouter, HTTPException
from app.services.telemetry_agent import telemetry_agent
from loguru import logger

router = APIRouter()

@router.get("/sessions/{session_id}/analytics")
async def get_session_analytics(session_id: str):
    """
    Retorna análisis de productividad para un caso específico (REPAIR PLAN V62.9).
    """
    try:
        res = await telemetry_agent.analyze_session_efficiency(session_id)
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return res
    except HTTPException as he: raise he
    except Exception as e:
        logger.error(f"❌ Error API Telemetría: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/productivity")
async def get_productivity_dashboard(days: int = 7):
    """
    Dashboard de gobernanza para análisis de productividad global.
    """
    try:
        return await telemetry_agent.get_global_metrics(days)
    except Exception as e:
        logger.error(f"❌ Error Dashboard Telemetría: {e}")
        raise HTTPException(status_code=500, detail=str(e))
