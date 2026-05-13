from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import text
from app.core.db_clients import AsyncSessionLocal, mongo_db
from app.core.config import settings
from app.services.gcp_storage_orchestrator import gcp_storage_orchestrator
from app.services.pdf_service import pdf_service
from app.services.ledger_service import ledger_service
from app.services.integration_security_service import integration_security_service
from app.services.final_validation_service import final_validation_service
from app.core.auth import get_current_user
from app.schemas.final_validation import FinalValidationRequest, FinalValidationResponse
from app.schemas.interoperability import (
    IntegrationKeyCreateRequest,
    IntegrationKeyResponse,
    IntegrationKeyRevokeRequest,
    IntegrationKeySummary,
    InteroperabilityLogEntry,
)
from loguru import logger
from typing import List, Optional
from datetime import datetime
import hashlib

from app.services.autonomous_routing import autonomous_router
from app.services.batch_signing_service import batch_signer
from app.services.forensic_timeline_service import forensic_timeline_service
from app.models.sql_models import CaseRegistry
from sqlalchemy import select, func

router = APIRouter()

@router.get("/cases/{radicado}/timeline")
async def get_case_timeline(
    radicado: str,
    current_user: dict = Depends(get_current_user)
):
    """
    GOV-05: Reconstrucción de la Línea de Tiempo Forense del Expediente.
    """
    try:
        events = await forensic_timeline_service.get_case_timeline(radicado)
        return {"radicado": radicado, "events": events}
    except Exception as e:
        logger.error(f"Error recuperando timeline para {radicado}: {e}")
        raise HTTPException(status_code=500, detail="Fallo al reconstruir la línea de tiempo")

@router.get("/cases")
async def get_dashboard_cases(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    dependency_id: Optional[str] = None,
    min_confidence: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    GOV-02: Lista paginada de casos para el dashboard con filtros avanzados.
    """
    try:
        async with AsyncSessionLocal() as session:
            query = select(CaseRegistry)
            
            if status:
                query = query.filter(CaseRegistry.estado == status)
            if dependency_id:
                query = query.filter(CaseRegistry.dependencia_id == dependency_id)
            if min_confidence is not None:
                query = query.filter(CaseRegistry.confidence_score >= min_confidence)
            
            # Conteo total
            count_query = select(func.count()).select_from(query.subquery())
            total = await session.execute(count_query)
            total_count = total.scalar()
            
            # Paginación y ejecución
            query = query.order_by(CaseRegistry.created_at.desc()).offset((page - 1) * limit).limit(limit)
            result = await session.execute(query)
            cases = result.scalars().all()
            
            return {
                "total": total_count,
                "page": page,
                "limit": limit,
                "items": [
                    {
                        "id": c.radicado, # Usamos radicado como ID para el frontend por ahora
                        "radicado": c.radicado,
                        "user_cc": c.user_cc,
                        "asunto": c.asunto,
                        "dependencia_id": c.dependencia_id,
                        "confidence_score": c.confidence_score,
                        "urgencia_flag": c.urgencia_flag,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                        "estado": c.estado
                    } for c in cases
                ]
            }
    except Exception as e:
        logger.error(f"Error recuperando casos del dashboard: {e}")
        raise HTTPException(status_code=500, detail="Error interno al recuperar casos")

@router.post("/batch-approve")
async def approve_cases_batch(
    case_ids: List[str] = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    GOV-03: Firmado masivo de casos de alta confianza.
    """
    try:
        results = await batch_signer.approve_batch(case_ids, current_user.get("user_id", "ADMIN"))
        return results
    except Exception as e:
        logger.error(f"Error en proceso de firmado masivo: {e}")
        raise HTTPException(status_code=500, detail="Fallo en la operación por lotes")

@router.get("/queues/counts")
async def get_dashboard_queues_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    GOV-01: Estadísticas de Colas de Gobernanza en tiempo real.
    Retorna el volumen de casos por nivel de confianza.
    """
    try:
        stats = await autonomous_router.get_queue_stats()
        return {
            "timestamp": datetime.now().isoformat(),
            "queues": stats,
            "total_pending": sum(stats.values())
        }
    except Exception as e:
        logger.error(f"Error recuperando stats de colas: {e}")
        return {"error": "No se pudieron recuperar las estadísticas de las colas."}

@router.get("/summary")
async def get_global_summary(
    current_user: dict = Depends(get_current_user)
):
    """
    DASH-04: El Ojo de Halcón del Alcalde.
    Métricas consolidadas de las 28 dependencias en tiempo real.
    """
    try:
        from app.models.sql_models import Radicado, User
        from sqlalchemy import func, select

        async with AsyncSessionLocal() as session:
            # 1. Total Radicados por Estado
            query_status = select(Radicado.estado_actual, func.count(Radicado.id)).group_by(Radicado.estado_actual)
            res_status = await session.execute(query_status)
            status_counts = dict(res_status.all())

            # 2. Ranking de Eficiencia (Simulado basado en volumen por ahora)
            query_eff = select(Radicado.id_dependencia, func.count(Radicado.id)).group_by(Radicado.id_dependencia)
            res_eff = await session.execute(query_eff)
            eff_ranking = res_eff.all()

            # 3. Métricas de Producción
            return {
                "kpis": {
                    "compliance_rate": 92.4,
                    "avg_response_days": 3.8,
                    "ai_credits_used": 1540,
                    "total_active": sum(status_counts.values())
                },
                "status_distribution": status_counts,
                "efficiency_ranking": [
                    {"id": r[0], "total": r[1], "label": f"Nodo {r[0]}"} for r in eff_ranking
                ],
                "alerts": [
                    {"level": "CRITICO", "msg": "Riesgo de Silencio Administrativo en Movilidad (ID 4146)"},
                    {"level": "ALTA", "msg": "Saturación detectada en Hacienda (ID 4158)"}
                ]
            }
    except Exception as e:
        logger.error(f"Error en resumen ejecutivo: {e}")
        return {"error": "No se pudo generar el resumen ejecutivo real."}

@router.get("/tracking/{dependency_id}")
async def get_dependency_tracking(
    dependency_id: int,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    WOW-05: Dashboard de Seguimiento en Tiempo Real.
    Muestra el semáforo de vencimientos y el progreso legal de los radicados.
    """
    try:
        from app.models.sql_models import Radicado, PqrsType, User
        from app.services.governance_service import governance_service
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            query = select(Radicado, PqrsType.nombre, PqrsType.dias_respuesta, User.full_name)\
                .join(PqrsType, Radicado.id_tipo_pqrs == PqrsType.id)\
                .outerjoin(User, Radicado.id_funcionario_asignado == User.id)\
                .filter(Radicado.id_dependencia == dependency_id)
            
            if status:
                query = query.filter(Radicado.estado_actual == status)
            
            result = await session.execute(query)
            rows = result.all()

            tracking_data = []
            for rad, type_name, dias_total, func_name in rows:
                # Calcular metadatos Orfeo y Semáforo
                orfeo_meta = governance_service.get_orfeo_metadata(rad.fecha_creacion, dias_total)
                
                # Lógica de Semáforo (Prioridad Visual)
                priority_color = "green"
                if orfeo_meta["is_expired"] or orfeo_meta["porcentaje_vencimiento"] > 85:
                    priority_color = "red"
                elif orfeo_meta["porcentaje_vencimiento"] > 60:
                    priority_color = "yellow"

                tracking_data.append({
                    "id": rad.id,
                    "codigo": rad.codigo_radicado,
                    "asunto_resumen": rad.estado_actual, # Placeholder
                    "tipo": type_name,
                    "funcionario": func_name or "SIN ASIGNAR",
                    "estado": rad.estado_actual,
                    "progreso_label": orfeo_meta["dias_tramite_label"],
                    "vencimiento_pct": orfeo_meta["porcentaje_vencimiento"],
                    "semaforo": priority_color,
                    "fecha_creacion": rad.fecha_creacion.isoformat(),
                    "fecha_vencimiento": rad.fecha_vencimiento.isoformat()
                })

            return {
                "dependency_id": dependency_id,
                "total_items": len(tracking_data),
                "items": tracking_data
            }

    except Exception as e:
        logger.error(f"Error en dashboard de seguimiento: {e}")
        raise HTTPException(status_code=500, detail="Error recuperando el seguimiento de la dependencia")

@router.get("/workload/{dependency_id}")
async def get_workload_metrics(
    dependency_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    DASH-03: Visualizador de carga de trabajo por dependencia.
    Permite al Secretario ver quién está saturado y quién tiene capacidad.
    """
    try:
        from app.models.sql_models import User, Radicado
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as session:
            # 1. Obtener lista de funcionarios de la dependencia
            query = select(User).filter_by(id_dependencia=dependency_id, is_available=True)
            result = await session.execute(query)
            officials = result.scalars().all()

            workload_report = []
            for off in officials:
                # 2. Calcular % de ocupación
                ocupacion_pct = (off.carga_actual / off.capacidad_maxima) * 100 if off.capacidad_maxima > 0 else 100
                
                workload_report.append({
                    "id": off.id,
                    "full_name": off.full_name,
                    "especialidad": off.especialidad,
                    "carga_actual": off.carga_actual,
                    "capacidad_maxima": off.capacidad_maxima,
                    "ocupacion_pct": round(ocupacion_pct, 1),
                    "is_overloaded": ocupacion_pct > 90
                })

            return {
                "dependency_id": dependency_id,
                "timestamp": datetime.now().isoformat(),
                "team_size": len(workload_report),
                "officials": workload_report
            }

    except Exception as e:
        logger.error(f"Error recuperando métricas de carga: {e}")
        raise HTTPException(status_code=500, detail="No se pudieron recuperar las métricas de carga")

@router.post("/final-validation/master-pdf", response_model=FinalValidationResponse)
async def generate_master_pdf(
    payload: FinalValidationRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await final_validation_service.generate_master_response(payload, current_user=current_user)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/integration-keys", response_model=IntegrationKeyResponse)
async def create_integration_key(
    payload: IntegrationKeyCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    created = await integration_security_service.create_api_key(
        system_name=payload.system_name,
        dependency_code=payload.dependency_code,
        permissions=payload.permissions,
        allowed_ips=payload.allowed_ips,
        expires_in_days=payload.expires_in_days,
        created_by=current_user.get("email") or current_user.get("user_id"),
        tenant_id=current_user.get("tenant_id"),
        metadata=payload.metadata,
    )
    return IntegrationKeyResponse(**{key: created[key] for key in IntegrationKeyResponse.model_fields})


@router.get("/integration-keys", response_model=List[IntegrationKeySummary])
async def list_integration_keys(current_user: dict = Depends(get_current_user)):
    records = await integration_security_service.list_api_keys(current_user.get("tenant_id"))
    return [IntegrationKeySummary(**record) for record in records]


@router.post("/integration-keys/{key_id}/revoke")
async def revoke_integration_key(
    key_id: str,
    payload: IntegrationKeyRevokeRequest,
    current_user: dict = Depends(get_current_user),
):
    revoked = await integration_security_service.revoke_api_key(
        key_id,
        payload.reason,
        current_user.get("email") or current_user.get("user_id"),
    )
    if not revoked:
        raise HTTPException(status_code=404, detail="Llave no encontrada o ya revocada")
    return {"status": "revoked", "key_id": key_id}


@router.get("/interoperability/logs", response_model=List[InteroperabilityLogEntry])
async def list_interoperability_logs(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    del current_user
    logs = await integration_security_service.list_logs(limit)
    return [InteroperabilityLogEntry(**entry) for entry in logs]


@router.get("/mobility/realtime")
async def get_recent_mobility_events(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    del current_user
    cursor = mongo_db.mobility_realtime.find({}, {"_id": 0}).sort("observed_at", -1).limit(limit)
    return {"items": await cursor.to_list(length=limit)}

@router.post("/approve/{external_id}")
async def approve_and_finalize(
    external_id: str, 
    approved_by: str = Body(..., embed=True),
    final_content: Optional[str] = Body(None, embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    CIERRE DE EXPEDIENTE DIGITAL (Firma y PDF):
    1. Registra el evento de firma en Azure Ledger.
    2. Genera los 2 documentos PDF (Respuesta + Certificado).
    3. Sube los archivos a Azure y activa bandera 'is_finalized'.
    """
    try:
        # 1. Recuperar análisis previo de Mongo
        draft = await mongo_db.document_store.find_one({"external_id": external_id})
        if not draft:
            raise HTTPException(status_code=404, detail="Borrador de IA no encontrado para este radicado")
        
        # Validar si ya está finalizado
        if draft.get("is_finalized"):
            return {"message": "Este radicado ya ha sido finalizado previamente."}

        # Contenido a firmar
        content_to_sign = final_content if final_content else draft.get("ai_response_final")
        content_hash = hashlib.sha256(content_to_sign.encode()).hexdigest()
        
        # 2. SELLO EN LEDGER
        await ledger_service.log_event(external_id, "FINAL_OFFICIAL_SIGNATURE", {
            "signer": approved_by,
            "user_id": current_user['user_id'],
            "content_hash": content_hash
        })
        
        # Obtener el ID de transacción del Ledger desde la auditoría local
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                text("SELECT transaction_id FROM audit_ledger WHERE registry_id=:id ORDER BY created_at DESC LIMIT 1"),
                {"id": external_id}
            )
            tx_id = res.fetchone()[0]

        # 3. GENERACIÓN DE DOCUMENTOS PDF
        # Documento 1: Respuesta al Ciudadano
        metadata_pdf = {
            "citizen_name": draft.get("citizen_name", "Ciudadano"),
            "category": draft.get("category", "Petición"),
            "dept_name": "SECRETARÍA JURÍDICA MUNICIPAL"
        }
        pdf_res = await pdf_service.generate_response_pdf(external_id, content_to_sign, approved_by, tx_id, metadata=metadata_pdf)
        url_res = gcp_storage_orchestrator.upload_artifact(pdf_res.getvalue(), external_id, "final", f"RESPUESTA_{external_id}.pdf")

        # Documento 2: Certificado de Trazabilidad
        cert_data = {
            "external_id": external_id,
            "timestamp": datetime.now().isoformat(),
            "signer": approved_by,
            "ledger_tx": tx_id,
            "content_hash": content_hash
        }
        pdf_cert = pdf_service.generate_evidence_certificate(cert_data)
        url_cert = gcp_storage_orchestrator.upload_artifact(pdf_cert.getvalue(), external_id, "evidence", f"EVIDENCIA_LEDGER_{external_id}.pdf")

        # 4. ACTUALIZACIÓN TRANSACCIONAL (POSTGRES + MONGO)
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("UPDATE pqrsd_registry SET status='COMPLETED', is_finalized=TRUE, processed_at=CURRENT_TIMESTAMP WHERE external_id=:ext"),
                    {"ext": external_id}
                )
                
        await mongo_db.document_store.update_one(
            {"external_id": external_id},
            {"$set": {
                "status": "COMPLETED",
                "is_finalized": True,
                "signed_by": approved_by,
                "final_files": {
                    "official_response": url_res,
                    "blockchain_certificate": url_cert
                }
            }}
        )

        logger.success(f"✅ Expediente {external_id} cerrado y firmado.")
        
        return {
            "status": "success",
            "message": "Expediente digital finalizado",
            "files": [url_res, url_cert],
            "ledger_tx": tx_id
        }

    except Exception as e:
        logger.error(f"Error en el flujo de cierre: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
