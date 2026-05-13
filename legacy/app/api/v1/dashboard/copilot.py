from fastapi import APIRouter, Depends, HTTPException, Body
from app.services.copilot_engine import copilot_engine
from app.core.auth import get_current_user
from loguru import logger
from typing import Dict, Any

router = APIRouter()

@router.post("/query")
async def ask_copilot(
    session_id: str = Body(..., embed=True),
    query: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    GOV-04: Consulta al Copiloto IA Contextual.
    """
    try:
        user_id = current_user.get("email") or "ADMIN"
        result = await copilot_engine.generate_response(session_id, query, user_id)
        return result
    except Exception as e:
        logger.error(f"Error en endpoint copilot: {e}")
        raise HTTPException(status_code=500, detail="Error al consultar al copiloto")
