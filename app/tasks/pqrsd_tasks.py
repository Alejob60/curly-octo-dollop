import os
import asyncio
import re
import json
import hashlib
from celery import Celery, chain
from loguru import logger
from sqlalchemy import text
from app.core.config import settings
from app.core.vertex_client import vertex_client
from app.core.db_clients import AsyncSessionLocal, mongo_db
from app.services.gcp_storage_orchestrator import gcp_storage_orchestrator
from app.services.ledger_service import ledger_service
from datetime import datetime

# Configuración de Motores (Valkey Cloud)
celery_app = Celery("orbital_worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

def _run_async(coro):
    """Ejecutor asíncrono seguro para Celery."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return asyncio.get_event_loop().run_until_complete(coro)

async def fetch_rag_context(query_text: str):
    """Busca leyes en MongoDB Atlas (RAG)."""
    try:
        from app.services.legal_citation_engine import legal_citation_engine
        # Extraer etiquetas del texto si es posible (simulado)
        citations = await legal_citation_engine.get_standardized_citations(["ley_1755_2015"])
        return "\n".join([f"- {c['norma']} Art {c['articulo']}: {c['texto_relevante']}" for c in citations])
    except:
        return "No se encontraron leyes específicas en la base de datos."

# --- CAPA REAL: VERTEX AI PIPELINE ---
@celery_app.task(name="process_gov_doc")
def process_gov_doc(file_content_base64: str = None, gcs_uri: str = None, mime_type: str = "application/pdf", file_hash: str = None):
    """
    REAL-02/03: Tarea de Celery que procesa el documento con Vertex AI.
    """
    async def run_extraction():
        try:
            from google.cloud import storage
            file_bytes = None
            
            # 1. Obtener contenido desde GCS
            if gcs_uri and gcs_uri.startswith("gs://"):
                bucket_name = gcs_uri.split("/")[2]
                blob_name = "/".join(gcs_uri.split("/")[3:])
                client = storage.Client(project=settings.GCP_PROJECT_ID)
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                file_bytes = blob.download_as_bytes()

            if not file_bytes:
                logger.warning(f"No se pudo recuperar el archivo para hash: {file_hash}")
                return {"status": "FAILED", "error": "No file content found"}

            # 2. IA: Vertex AI Extraction (Ciego)
            prompt = "Extrae datos estructurados (Asunto, Peticionario, Hechos) de este documento oficial."
            result = await vertex_client.generate_content([prompt])

            # 3. Guardar en MongoDB para Polling (REAL-04)
            await mongo_db.task_results.update_one(
                {"task_id": process_gov_doc.request.id},
                {"$set": {
                    "status": "SUCCESS",
                    "result": result,
                    "file_hash": file_hash,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
            return result

        except Exception as e:
            logger.error(f"Error en process_gov_doc: {str(e)}")
            raise e

    return _run_async(run_extraction())

# --- CAPA 1: MASKING AVANZADO ---
@celery_app.task(name="task_ocr_and_mask")
def task_ocr_and_mask(pqrsd_data: dict):
    async def run_masking():
        content = pqrsd_data.get("content", "")
        # Regex básica + Inferencia Vertex (Ciega)
        content = re.sub(r'\b\d{7,15}\b', '[ID_PROTEGIDA]', content)
        content = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w{2,4}\b', '[EMAIL_PROTEGIDO]', content)
        
        prompt = f"Anonimiza nombres propios en este texto PQRSD: {content}"
        try:
            masked = await vertex_client.generate_content([prompt])
            pqrsd_data["masked_content"] = masked or content
        except:
            pqrsd_data["masked_content"] = content
        return pqrsd_data

    return _run_async(run_masking())

# --- CAPA 2: ANÁLISIS JURÍDICO RAG ---
@celery_app.task(name="task_ia_operation")
def task_ia_operation(pqrsd_data: dict):
    async def process_rag():
        context = await fetch_rag_context(pqrsd_data.get("masked_content", ""))
        prompt = f"""
        SISTEMA ORBITAL PRIME - ANALISTA JURÍDICO GCP
        CONTEXTO LEGAL: {context}
        SOLICITUD: {pqrsd_data.get('masked_content')}
        INSTRUCCIÓN: Proyecta una respuesta técnica citando las leyes.
        """
        try:
            draft = await vertex_client.generate_content([prompt])
            res = {"external_id": pqrsd_data["external_id"], "ai_response_final": draft}
            await mongo_db.document_store.insert_one(res)
            return res
        except Exception as e:
            logger.error(f"Fallo IA Task: {e}")
            return {"error": str(e)}

    pqrsd_data["analysis"] = _run_async(process_rag())
    return pqrsd_data

@celery_app.task(name="task_final_ai_review")
def task_final_ai_review(pqrsd_data: dict):
    async def run_review():
        analysis = pqrsd_data.get("analysis", {})
        draft = analysis.get("ai_response_final", "")
        if not draft: return pqrsd_data

        prompt = f"Actúa como revisor legal senior. Mejora la coherencia y tono de este borrador PQRSD: {draft}"
        try:
            reviewed = await vertex_client.generate_content([prompt])
            pqrsd_data["analysis"]["ai_response_final"] = reviewed or draft
        except:
            pass
        return pqrsd_data

    return _run_async(run_review())

# --- CAPA 3: NOTIFICACIÓN Y LEDGER (GCP-NATIVE) ---
@celery_app.task(name="task_notify_and_ledger")
def task_notify_and_ledger(pqrsd_data: dict):
    async def finalize():
        from app.services.notification_service import notification_service
        # Sello en Ledger Inmutable (GCP-WORM)
        await ledger_service.log_event(pqrsd_data["external_id"], "GCP_PIPELINE_COMPLETE", {"provider": "GCP"})
        
        # Notificar (GCP-Relay)
        if pqrsd_data.get("citizen_email"):
            await notification_service.send_official_radicado_email(
                recipient_email=pqrsd_data["citizen_email"],
                citizen_name=pqrsd_data.get("citizen_name", "Ciudadano"),
                radicado_id=pqrsd_data["external_id"],
                pdf_paths=[] # PDFs se generan en el flujo principal
            )
        
        async with AsyncSessionLocal() as session:
            await session.execute(text("UPDATE pqrsd_registry SET status='ANALYZED' WHERE external_id=:id"), {"id": pqrsd_data["external_id"]})
            await session.commit()

    return _run_async(finalize())

# --- CAPA 4: PROCESAMIENTO E2E ASÍNCRONO ---
@celery_app.task(name="task_finalize_and_sign_async")
def task_finalize_and_sign_async(audit_data: dict, user_ip: str, session_id: str):
    async def run_finalize():
        from app.services.judicial_engine_service import judicial_engine
        try:
            logger.info(f"🚀 [WORKER] Iniciando Firma y Rehidratación GCP para sesión: {session_id}")
            result = await judicial_engine.finalize_and_sign_pqrsd(
                audit_data=audit_data,
                user_ip=user_ip,
                session_id=session_id
            )
            return result
        except Exception as e:
            logger.error(f"❌ [WORKER] Fallo en radicación asíncrona GCP: {e}")
            return {"status": "error", "message": str(e)}

    return _run_async(run_finalize())
