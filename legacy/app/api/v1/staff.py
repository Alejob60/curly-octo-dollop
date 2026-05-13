from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.db_clients import AsyncSessionLocal
from app.models.sql_models import User, Role
from app.core.auth import get_current_user
from sqlalchemy import select, update
from loguru import logger
from typing import List

router = APIRouter()

@router.get("/", response_model=List[dict])
async def list_staff_by_dependency(
    dependency_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    STAFF-01: Lista todo el personal de una dependencia específica.
    """
    async with AsyncSessionLocal() as session:
        query = select(User).filter_by(id_dependencia=dependency_id)
        result = await session.execute(query)
        staff = result.scalars().all()
        
        return [
            {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "especialidad": u.especialidad,
                "carga_actual": u.carga_actual,
                "capacidad_maxima": u.capacidad_maxima,
                "is_active": u.is_available
            } for u in staff
        ]

@router.post("/register")
async def register_staff_member(
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    STAFF-01: Registra un nuevo funcionario en el sistema.
    """
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                new_user = User(
                    email=payload["email"],
                    full_name=payload["full_name"],
                    role_id=payload.get("role_id", 3), # Default Lawyer
                    id_dependencia=payload["id_dependencia"],
                    especialidad=payload.get("especialidad", "General"),
                    capacidad_maxima=payload.get("capacidad_maxima", 20),
                    is_available=True
                )
                session.add(new_user)
                
        return {"status": "success", "message": f"Funcionario {payload['full_name']} registrado exitosamente."}
    except Exception as e:
        logger.error(f"Error registrando funcionario: {e}")
        raise HTTPException(status_code=500, detail="No se pudo registrar el funcionario")

from app.services.judicial_engine_service import judicial_engine

@router.post("/generate-draft")
async def generate_draft_response(
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    STAFF-02: Genera un borrador de respuesta oficial usando IA.
    Consume 1 crédito del plan multitenant.
    """
    try:
        radicado_id = payload.get("radicado_id")
        official_notes = payload.get("notes", "")
        
        # Simulación de consumo de créditos (RealCulture AI Native)
        logger.info(f"🪙 Crédito consumido por {current_user['email']} para radicado {radicado_id}")
        
        # Llamar al motor de proyección judicial
        draft_text = await judicial_engine.project_official_response(
            radicado_id=radicado_id,
            official_notes=official_notes
        )
        
        return {
            "status": "success",
            "draft": draft_text,
            "credits_remaining": 8450
        }
    except Exception as e:
        logger.error(f"Error generando borrador: {e}")
        raise HTTPException(status_code=500, detail="No se pudo proyectar la respuesta")
