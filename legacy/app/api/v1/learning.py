from fastapi import APIRouter, HTTPException
from app.core.db_clients import mongo_db
from loguru import logger
import datetime

router = APIRouter()

@router.post("/capture")
async def capture_learning_event(payload: dict):
    """
    LEARN-01: Captura la corrección humana sobre una respuesta de la IA.
    Esto alimenta la Memoria Institucional de Orbital Prime.
    """
    try:
        # Estructura del evento de aprendizaje
        learning_event = {
            "radicado_id": payload.get("radicado_id"),
            "contexto_legal_ids": payload.get("contexto_ids", []), # IDs de Atlas usados
            "input_ciudadano": payload.get("input_ciudadano"),
            "propuesta_ia": payload.get("propuesta_ia"),
            "correccion_humana": payload.get("correccion_humana"),
            "funcionario_id": payload.get("funcionario_id"),
            "dependencia_id": payload.get("dependencia_id"),
            "diferencia_semantica": payload.get("diff_score", 0.0),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "status": "PENDING_FINE_TUNING"
        }
        
        result = await mongo_db.ai_experience.insert_one(learning_event)
        
        logger.success(f"Evento de aprendizaje capturado para radicado {payload.get('radicado_id')}")
        
        return {
            "status": "success",
            "learning_id": str(result.inserted_id),
            "message": "Criterio jurídico capturado para evolución del modelo."
        }

    except Exception as e:
        logger.error(f"Error capturando aprendizaje: {e}")
        raise HTTPException(status_code=500, detail="Error en Experience Store")

@router.post("/citizen-feedback")
async def capture_citizen_feedback(payload: dict):
    """
    WOW-06: Captura la calificación del ciudadano (NPS).
    """
    try:
        feedback = {
            "radicado_id": payload.get("radicado_id"),
            "rating": payload.get("rating"), # 1-5 estrellas
            "comment": payload.get("comment"),
            "channel": payload.get("channel", "WHATSAPP"),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        await mongo_db.citizen_satisfaction.insert_one(feedback)
        logger.success(f"Feedback ciudadano recibido para radicado {payload.get('radicado_id')}")
        return {"status": "success", "message": "Gracias por calificar nuestro servicio."}
    except Exception as e:
        logger.error(f"Error capturando feedback ciudadano: {e}")
        raise HTTPException(status_code=500, detail="Error procesando calificación")

@router.get("/metrics")
async def get_learning_metrics():
    """
    KPI-02 / WOW-06: Obtiene métricas de mejora de la IA y Satisfacción Ciudadana.
    """
    try:
        # Métricas de IA
        total_learn = await mongo_db.ai_experience.count_documents({})
        corrected = await mongo_db.ai_experience.count_documents({"diferencia_semantica": {"$gt": 0.1}})
        
        # Métricas de Ciudadano (Reto 3)
        total_feedback = await mongo_db.citizen_satisfaction.count_documents({})
        if total_feedback > 0:
            pipeline = [
                {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}}
            ]
            cursor = mongo_db.citizen_satisfaction.aggregate(pipeline)
            res = await cursor.to_list(length=1)
            avg_nps = res[0]["avg_rating"] if res else 0
        else:
            avg_nps = 0
            
        return {
            "ia_quality": {
                "total_lecciones": total_learn,
                "tasa_correccion_humana": (corrected / total_learn) if total_learn > 0 else 0,
                "ahorro_fiscal_estimado_usd": total_learn * 15
            },
            "citizen_satisfaction": {
                "total_respuestas": total_feedback,
                "nps_promedio": round(avg_nps, 2),
                "satisfaccion_label": "EXCELENTE" if avg_nps > 4 else "BUENA" if avg_nps > 3 else "POR MEJORAR"
            }
        }
    except Exception as e:
        logger.error(f"Error en métricas consolidado: {e}")
        return {"error": "Métricas no disponibles"}

from app.models.sql_models import Radicado, Asignacion, Trazabilidad
from app.core.db_clients import AsyncSessionLocal
from sqlalchemy import select

from app.services.signature_service import signature_service

from app.services.pdf_service import pdf_service
from app.services.gcp_storage_service import immutable_storage_service
from app.services.traceability_service import traceability_service

from app.services.learning_service import learning_service
from app.core.db_clients import mongo_db

from app.services.notification_service import notification_service

from app.core.google_workspace_client import google_workspace

@router.post("/approve/{radicado_id}")
async def approve_resolution(radicado_id: str, payload: dict):
    """
    FLOW-02 / SEC-03 / ARC-01 / MAIL-02 / CAL-02: Cierre Total Enterprise.
    """
    try:
        funcionario_id = str(payload.get("funcionario_id"))
        final_text = payload.get("final_text")

        # 1. Firmar y Generar PDF (Lógica existente)
        signature_hash = signature_service.generate_electronic_signature(final_text, funcionario_id)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                query = select(Radicado).filter_by(codigo_radicado=radicado_id)
                result = await session.execute(query)
                radicado = result.scalars().first()
                if not radicado: raise HTTPException(status_code=404, detail="No existe")

                qr_path = traceability_service.generate_qr_tracking(radicado_id, signature_hash)
                
                doc_payload = {
                    "radicado": radicado_id, "citizen_name": payload.get("citizen_name", "Ciudadano"),
                    "content": final_text, "dependency_name": "Soberanía Jurídica",
                    "hash_ledger": signature_hash, "qr_path": qr_path
                }
                pdf_path = pdf_service.generate_legal_document(doc_payload)

                # 2. COMUNICACIONES OFICIALES REALES (Fase 19)
                # Enviar Email Institucional
                email_body = f"<h2>Resolución de Trámite {radicado_id}</h2><p>Adjunto encontrará el acto administrativo firmado.</p>"
                await google_workspace.send_official_email(
                    to_email=payload.get("citizen_email", "ciudadano@cali.gov.co"),
                    subject=f"ALCALDÍA DE CALI: Respuesta Radicado {radicado_id}",
                    body=email_body,
                    attachment_path=pdf_path
                )

                # Agendar en Calendar
                await google_workspace.schedule_legal_event({
                    "summary": f"🏁 FINALIZADO: {radicado_id}",
                    "start": datetime.datetime.utcnow().isoformat(),
                    "description": f"Trámite cerrado legalmente con firma SHA: {signature_hash[:8]}"
                })

                radicado.estado_actual = "CERRADO"
                radicado.hash_seguridad = signature_hash
                
                audit = Trazabilidad(
                    radicado_id=radicado.id, estado_anterior="PENDIENTE",
                    estado_nuevo="CERRADO", id_funcionario=funcionario_id,
                    comentario="Cierre Enterprise: Gmail y Calendar sincronizados."
                )
                session.add(audit)

        return {"status": "success", "radicado": radicado_id, "pdf": pdf_path}

    except Exception as e:
        logger.error(f"Error en cierre Enterprise: {e}")
        raise HTTPException(status_code=500, detail="Fallo en sincronización Workspace")

    except Exception as e:
        logger.error(f"Error en cierre jurídico total: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Fallo en el proceso de firma y archivado")
