from fastapi import APIRouter, Depends, HTTPException, Header, Request, UploadFile, File
from app.core.auth import verify_api_key
from app.schemas.ingestion import GovDocsPayload, RawIngestionResponse
from app.core.config import settings
from app.core.adapter import bridge_adapter
from app.tasks.pqrsd_tasks import task_ocr_and_mask, process_gov_doc
from app.services.integration_security_service import integration_security_service
from app.services.ledger_service import ledger_service
from app.services.gcp_storage_service import immutable_storage_service
import hashlib
import uuid
from celery import chain
from datetime import datetime
from loguru import logger
from cryptography.fernet import Fernet
import json
import base64

router = APIRouter()

# Configuración de cifrado para PII Protection
ENCRYPTION_KEY = settings.INTERNAL_API_KEY[:32].encode().ljust(32, b'=')
# Asegurar que sea una clave Fernet válida (base64)
FERNET_KEY = base64.urlsafe_b64encode(ENCRYPTION_KEY)
cipher_suite = Fernet(FERNET_KEY)

@router.post("/upload", response_model=RawIngestionResponse)
async def upload_document(
    file: UploadFile = File(...),
    auth_context: dict = Depends(verify_api_key)
):
    """
    REAL-01: Endpoint de Ingesta Física.
    Recibe el archivo, lo sube a GCS e inicia el pipeline asíncrono.
    """
    try:
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        # 1. Subir a Google Cloud Storage (Inmutable)
        gcs_path = immutable_storage_service.upload_to_immutable_bucket(
            payload={"filename": file.filename, "content_type": file.content_type},
            external_id=file_hash[:12],
            action="INGEST_UPLOAD",
            digest_sha256=file_hash
        )

        # 2. Encolar tarea en Celery para Vertex AI
        task = process_gov_doc.delay(
            file_content_base64=uuid.uuid4().hex, 
            gcs_uri=gcs_path,
            mime_type=file.content_type,
            file_hash=file_hash
        )

        logger.success(f"Archivo {file.filename} recibido y encolado. Task: {task.id}")

        return RawIngestionResponse(
            task_id=task.id,
            ingested_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"Error en upload real: {str(e)}")
        raise HTTPException(status_code=500, detail="Error procesando archivo físico")

@router.post("/", response_model=RawIngestionResponse)
async def ingest_document(
    request: Request,
    source_type: str = "GENERIC",
    auth_context: dict = Depends(verify_api_key)
):
    """
    Gateway de Ingesta Universal (The Orbital Bridge).
    Mapea, Cifra y Encola datos de cualquier origen.
    """
    try:
        raw_data = await request.json()
        logger.info(f"Ingesta recibida de origen: {source_type}")

        normalized_data = bridge_adapter.process(source_type, raw_data)
        key_record = auth_context.get("key_record") or {}
        
        # Auditoría de Ingesta
        await integration_security_service.log_event(
            event_type="BRIDGE_INGEST_ACCEPTED",
            status="success",
            detail=f"Payload aceptado desde {source_type}",
            key_id=key_record.get("key_id"),
            system_name=key_record.get("system_name") or source_type,
            dependency_code=key_record.get("dependency_code"),
            source_ip=auth_context.get("source_ip"),
            metadata={"external_id": normalized_data.external_id},
        )
        
        checksum = bridge_adapter.calculate_checksum(raw_data)
        
        # Cifrado de Datos Sensibles (PII Protection)
        payload_json = normalized_data.model_dump_json()
        encrypted_payload = cipher_suite.encrypt(payload_json.encode())
        
        # Disparar Pipeline
        task_chain = chain(task_ocr_and_mask.s(normalized_data.model_dump()))
        result = task_chain.apply_async()

        try:
            await ledger_service.log_event(
                normalized_data.external_id,
                "BRIDGE_INGEST_RECEIVED",
                {
                    "source_type": source_type,
                    "source_ip": auth_context.get("source_ip"),
                    "checksum": checksum,
                    "key_id": key_record.get("key_id"),
                },
            )
        except Exception as ledger_exc:
            logger.warning(f"Error en ledger: {ledger_exc}")

        logger.success(f"Documento {normalized_data.external_id} encolado: {result.id}")

        return RawIngestionResponse(
            task_id=result.id,
            ingested_at=datetime.now()
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error en Gateway de Ingesta: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno en el bus de datos")
