from fastapi import APIRouter, HTTPException, Body, Depends
from app.core.db_clients import AsyncSessionLocal
from app.services.ledger_service import ledger_service
from app.core.auth import get_current_user
from app.models.sql_models import AccionDependencia, Radicado, Trazabilidad
from sqlalchemy import select
from loguru import logger
import datetime
import json
import uuid
import hashlib

router = APIRouter()

@router.post("/action/{radicado_id}")
async def log_dependency_action(
    radicado_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Rastrea qué hace la dependencia con el radicado.
    Ej: "Visita técnica programada para el 25/04".
    """
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                # 1. Buscar ID interno del radicado
                query = select(Radicado).filter_by(codigo_radicado=radicado_id)
                res = await session.execute(query)
                radicado = res.scalars().first()
                
                if not radicado:
                    raise HTTPException(status_code=404, detail="Radicado no encontrado")

                # 2. Registrar la Acción Operativa
                nueva_accion = AccionDependencia(
                    radicado_id=radicado.id,
                    funcionario_id=current_user.get("id", 1),
                    tipo_accion=payload.get("tipo_accion"),
                    descripcion=payload.get("descripcion"),
                    resultado=payload.get("resultado", "EN_PROCESO")
                )
                session.add(nueva_accion)

                # 3. Registrar en Trazabilidad General
                audit = Trazabilidad(
                    radicado_id=radicado.id,
                    estado_anterior=radicado.estado_actual,
                    estado_nuevo=radicado.estado_actual,
                    id_funcionario=str(current_user.get("id", 1)),
                    comentario=f"Actuación Operativa: {payload.get('tipo_accion')} - {payload.get('descripcion')}"
                )
                session.add(audit)

        return {"status": "success", "message": "Actuación registrada en la bitácora de la dependencia."}

    except Exception as e:
        logger.error(f"Error registrando acción de dependencia: {e}")
        raise HTTPException(status_code=500, detail="Error interno en bitácora")

@router.post("/finalize")
async def finalize_radicado(session_id: str = Body(..., embed=True)):
    """
    Cierra el flujo de Misybot y radica oficialmente en la Alcaldía.
    """
    # (Mantenemos compatibilidad con Misybot si es necesario)
    return {"message": "Endpoint migrado a citizen/radicar"}
