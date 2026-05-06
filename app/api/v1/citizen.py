from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import List
from app.core.config import settings
from app.core.db_clients import AsyncSessionLocal
from app.services.gcp_storage_orchestrator import gcp_storage_orchestrator
from app.tasks.pqrsd_tasks import task_ocr_and_mask, task_ia_operation, task_final_ai_review, task_notify_and_ledger
from celery import chain
from sqlalchemy import text
import uuid
import os
from loguru import logger

router = APIRouter()

from app.services.integration_security_service import integration_security_service
from app.services.ledger_service import ledger_service
from app.core.db_clients import mongo_db
import datetime

from app.services.governance_service import governance_service

from app.services.assignment_service import assignment_service

@router.post("/radicar")
async def final_radication(
    payload: dict,
):
    """
    REAL-07: Cierre Jurídico, Sellado del Ledger y Reparto Dinámico.
    """
    try:
        # 1. Generar Radicado Oficial
        radicado_id = f"OP-2026-{uuid.uuid4().hex[:6].upper()}"
        
        # ... (Lógica de Ledger y Anonimización se mantiene) ...
        # 3. REAL-07: Sellado en el Ledger Inmutable
        hash_ledger = hashlib.sha256(f"{payload.get('citizen_id')}|{payload.get('hash')}|{datetime.datetime.utcnow().isoformat()}".encode()).hexdigest()
        
        # 4. Gobernanza en PostgreSQL
        try:
            dep_id = int(payload.get("selected_dependency_id") or 4112)
            type_id = int(payload.get("pqrs_type_id") or 1)
        except:
            dep_id = 4112
            type_id = 1

        async with AsyncSessionLocal() as session:
            async with session.begin():
                # Registro inicial de gobernanza
                new_radicado = await governance_service.register_radicado(session, {
                    "codigo_radicado": radicado_id,
                    "hash_seguridad": hash_ledger,
                    "id_usuario": payload.get("citizen_id", "ANONYMOUS"),
                    "id_dependencia": dep_id,
                    "id_tipo_pqrs": type_id
                })
                
                # LOGIC-01: REPARTO AUTOMÁTICO
                await assignment_service.assign_to_best_official(
                    session, 
                    new_radicado.id, 
                    dep_id
                )

                if payload.get("hash"):
                    from app.models.sql_models import EvidenciaBucket
                    evidencia = EvidenciaBucket(
                        radicado_id=new_radicado.id,
                        gcs_uri=f"gs://orbital-prime-docs/radicados/{payload.get('hash')}.pdf",
                        tipo_documento="ORIGINAL_CIUDADANO"
                    )
                    session.add(evidencia)

        # 5. Persistencia Documental
        await mongo_db.final_records.insert_one({
            **payload,
            "radicado": radicado_id,
            "hash_ledger": hash_ledger,
            "created_at": datetime.datetime.utcnow()
        })
        
        return {
            "status": "success",
            "radicado": radicado_id,
            "message": "Trámite radicado, asignado y gobernado exitosamente."
        }
        
    except Exception as e:
        logger.error(f"Error en radicación final con gobernanza: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error al sellar el radicado")

@router.post("/submit")
async def citizen_submit(
    citizen_name: str = Form(...),
    citizen_id: str = Form(...),
    citizen_email: str = Form(...),
    content: str = Form(...),
    pqrs_type_id: str = Form("PETICION_GENERAL"),
    selected_dependency_id: str = Form(""),
    suggested_dependency_id: str = Form(""),
    routing_confidence_score: float = Form(0.0),
    files: List[UploadFile] = File(default=[])
):
    """
    Endpoint para el Portal Ciudadano (Canal B).
    Recibe datos estructurados y archivos adjuntos.
    """
    external_id = f"WEB-{uuid.uuid4().hex[:8].upper()}"
    attachment_url = None
    attachment_urls = []

    try:
        # 1. Guardar archivos en GCP Storage si existen
        for file in files:
            file_content = await file.read()
            uploaded_url = gcp_storage_orchestrator.upload_artifact(
                file_content, external_id, "incoming", file.filename
            )
            attachment_urls.append(uploaded_url)

        attachment_url = attachment_urls[0] if attachment_urls else None

        manual_override = bool(
            suggested_dependency_id
            and selected_dependency_id
            and suggested_dependency_id != selected_dependency_id
        )

        # 2. Crear registro en Postgres
        async with AsyncSessionLocal() as session:
            async with session.begin():
                query = text("""
                    INSERT INTO pqrsd_registry 
                    (external_id, source_type, citizen_id, citizen_name, citizen_email, status, attachment_url, target_department_id)
                    VALUES (:ext_id, 'DIRECT_PORTAL', :c_id, :c_name, :c_email, 'RECEIVED', :url, :target_department_id)
                    RETURNING id
                """)
                result = await session.execute(query, {
                    "ext_id": external_id,
                    "c_id": citizen_id,
                    "c_name": citizen_name,
                    "c_email": citizen_email,
                    "url": attachment_url,
                    "target_department_id": selected_dependency_id or None,
                })
                internal_id = result.fetchone()[0]

        # 3. Lanzar Pipeline de Procesamiento
        payload = {
            "registry_id": str(internal_id),
            "external_id": external_id,
            "citizen_name": citizen_name,
            "citizen_id": citizen_id,
            "citizen_email": citizen_email,
            "content": content,
            "attachment_url": attachment_url,
            "attachment_urls": attachment_urls,
            "pqrs_type_id": pqrs_type_id,
            "selected_dependency_id": selected_dependency_id,
            "suggested_dependency_id": suggested_dependency_id,
            "routing_confidence_score": routing_confidence_score,
            "manual_override": manual_override,
        }

        # Registro para aprendizaje del Cali-Lex Advisor
        from app.core.db_clients import mongo_db

        await mongo_db.routing_feedback.insert_one(
            {
                "external_id": external_id,
                "topic": content[:500],
                "pqrs_type_id": pqrs_type_id,
                "suggested_dependency_id": suggested_dependency_id or None,
                "selected_dependency_id": selected_dependency_id or None,
                "routing_confidence_score": routing_confidence_score,
                "manual_override": manual_override,
            }
        )
        
        # Encadenar tareas
        workflow = chain(
            task_ocr_and_mask.s(payload),
            task_ia_operation.s(),
            task_final_ai_review.s(),
            task_notify_and_ledger.s()
        )
        task_result = workflow.apply_async()

        # Actualizar task_id en DB
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    text("UPDATE pqrsd_registry SET task_id = :tid WHERE external_id = :eid"),
                    {"tid": task_result.id, "eid": external_id}
                )

        return {
            "status": "success",
            "radicado": external_id,
            "manual_override": manual_override,
            "selected_dependency_id": selected_dependency_id,
            "suggested_dependency_id": suggested_dependency_id,
            "message": "Su solicitud ha sido recibida y está siendo procesada por el motor de IA."
        }

    except Exception as e:
        logger.error(f"Error en ingesta ciudadana: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al procesar solicitud")
