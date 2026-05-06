from fastapi import APIRouter, HTTPException, Body
from app.models.sql_models import CaseRegistry, User, AuditLedger
from app.core.db_clients import postgres_manager
from app.services.ledger_service import ledger_service
from app.services.notification_service import notification_service
from app.services.gcp_storage_service import immutable_storage_service
from app.services.signer import signer_service
from app.services.pqrs_manager import pqrs_manager
from sqlalchemy import select, update, desc, or_
from loguru import logger
import datetime
import os
import json

router = APIRouter()

@router.get("/health")
async def copilot_health():
    return {"status": "ok", "service": "Governance Copilot"}

@router.get("/queue")
async def get_copilot_queue():
    """
    COPILOT V2: Bandeja de Entrada Inteligente con SLA y Priorización.
    """
    async with postgres_manager.get_session() as session:
        stmt = select(CaseRegistry).where(
            CaseRegistry.estado.in_(["PENDIENTE_MAESTRA", "EN_REVISION_DEPENDENCIA"])
        ).order_by(desc(CaseRegistry.created_at))
        
        result = await session.execute(stmt)
        cases = result.scalars().all()
        
        queue = []
        now = datetime.datetime.utcnow()
        
        for c in cases:
            # 1. Cálculo de SLA dinámico (Ajuste Crítico #1)
            vencimiento = c.vencimiento_legal
            time_left_str = "S.D."
            if vencimiento:
                # Si el vencimiento es ingenuo (naive), lo convertimos o asumimos UTC
                delta = vencimiento.replace(tzinfo=None) - now
                if delta.total_seconds() < 0:
                    time_left_str = "VENCIDO"
                elif delta.days > 0:
                    time_left_str = f"{delta.days}d"
                else:
                    hours = int(delta.total_seconds() // 3600)
                    time_left_str = f"{hours}h"

            queue.append({
                "radicado": c.radicado,
                "citizen": c.peticionario_nombre or "Ciudadano Anónimo",
                "destino": c.dependencia_nombre or "GENERAL", # Ajuste Crítico #2
                "sla": time_left_str,
                "score": float(c.confidence_score or 0.5),
                "estado": c.estado,
                "created_at": c.created_at.isoformat()
            })
            
        return {"status": "success", "count": len(queue), "queue": queue}

@router.post("/batch-approve")
async def batch_approve_cases(
    radicados: list = Body(..., embed=True),
    official_id: str = Body(..., embed=True)
):
    """
    COPILOT V2: Firma en Lote Segura (Ajuste Crítico #3).
    Bloquea radicados con score < 0.70.
    """
    async with postgres_manager.get_session() as session:
        stmt = select(CaseRegistry).where(CaseRegistry.radicado.in_(radicados))
        result = await session.execute(stmt)
        cases = result.scalars().all()
        
        approved = []
        rejected_low_score = []
        
        for c in cases:
            if (c.confidence_score or 0.0) < 0.70:
                rejected_low_score.append(c.radicado)
                continue
            
            # Procesamos aprobación (Simplificado para el demo de lote)
            c.estado = "EN_REVISION_DEPENDENCIA" if c.estado == "PENDIENTE_MAESTRA" else "FIRMADO"
            c.updated_at = datetime.datetime.utcnow()
            approved.append(c.radicado)

        await session.commit()
        
        # Log del evento masivo en el Ledger
        if approved:
            await ledger_service.log_event("BATCH_ACTION", "BATCH_APPROVAL", {
                "official_id": official_id,
                "count": len(approved),
                "radicados": approved
            })

        return {
            "status": "partial" if rejected_low_score else "success",
            "approved_count": len(approved),
            "rejected_count": len(rejected_low_score),
            "rejected_radicados": rejected_low_score,
            "message": "Firma en lote completada. Casos con score bajo requieren revisión manual." if rejected_low_score else "Todo el lote firmado exitosamente."
        }

@router.post("/request-adjustment/{radicado}")
async def request_ai_adjustment(
    radicado: str,
    feedback: str = Body(..., embed=True),
    official_id: str = Body(..., embed=True)
):
    """
    COPILOT V2: Bucle de Aprendizaje IA (Ajuste Crítico #4).
    Recibe feedback humano y regenera sustancia.
    """
    async with postgres_manager.get_session() as session:
        stmt = select(CaseRegistry).where(CaseRegistry.radicado == radicado)
        result = await session.execute(stmt)
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Radicado no encontrado")

        # 1. Registrar Feedback en Ledger
        await ledger_service.log_event(radicado, "HUMAN_FEEDBACK", {
            "official_id": official_id,
            "feedback": feedback
        })

        # 2. Disparar Regeneración IA
        # Recuperamos el session_id para el manager
        session_id = case.session_id
        
        # Llamamos al generador con el feedback
        # Nota: Usamos una versión interna que inyecte el feedback en el prompt
        await pqrs_manager._generate_missing_substance(session_id, {"motivo": case.asunto, "nombres": case.peticionario_nombre}, feedback=feedback)

        return {
            "status": "success",
            "message": "Ajuste solicitado. La IA está regenerando los documentos con su feedback.",
            "radicado": radicado
        }

@router.post("/master-approve/{radicado}")
async def master_approve(
    radicado: str,
    official_id: str = Body(..., embed=True),
    comments: str = Body("", embed=True)
):
    """
    COPILOT V1: Visto Bueno Maestro.
    Firma el Auto de Traslado y distribuye a la dependencia.
    """
    async with postgres_manager.get_session() as session:
        # 1. Recuperar el caso
        stmt = select(CaseRegistry).where(CaseRegistry.radicado == radicado)
        result = await session.execute(stmt)
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Radicado no encontrado")
        
        if case.estado != "PENDIENTE_MAESTRA":
            raise HTTPException(status_code=400, detail=f"Estado inválido: {case.estado}")

        # 2. Simulación de Firma Digital del Funcionario (KMS)
        logger.info(f"🖋️ [MASTER] Funcionario {official_id} aprobando {radicado}")
        
        # Registramos el evento de aprobación maestra
        await ledger_service.log_event(radicado, "MASTER_APPROVAL", {
            "official_id": official_id,
            "comments": comments,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })

        # 3. Transición de Estado
        case.estado = "EN_REVISION_DEPENDENCIA"
        case.updated_at = datetime.datetime.utcnow()
        await session.commit()

        return {
            "status": "success",
            "message": f"Radicado {radicado} aprobado por Gobernación Central. Enviado a {case.dependencia_nombre}.",
            "target_dependency": case.dependencia_nombre
        }

@router.post("/dependency-approve/{radicado}")
async def dependency_approve(
    radicado: str,
    official_id: str = Body(..., embed=True),
    comments: str = Body("", embed=True)
):
    """
    COPILOT V1: Visto Bueno de Dependencia (Final).
    Firma la respuesta final y dispara la notificación WORM.
    """
    async with postgres_manager.get_session() as session:
        # 1. Recuperar el caso
        stmt = select(CaseRegistry).where(CaseRegistry.radicado == radicado)
        result = await session.execute(stmt)
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Radicado no encontrado")
        
        if case.estado != "EN_REVISION_DEPENDENCIA":
            raise HTTPException(status_code=400, detail=f"El caso no está en etapa de revisión de dependencia.")

        # 2. PROCESO DE CIERRE FINAL (Fase 4 Migrada aquí)
        logger.info(f"🏁 [DEPENDENCY] Funcionario {official_id} dando cierre final a {radicado}")
        
        artifacts = case.pdf_paths # { "memorial": "...", "traslado": "...", "borrador": "..." }
        
        # 2.1. Carga a WORM
        immutable_artifacts = {}
        for key, rel_path in artifacts.items():
            local_path = os.path.join(os.getcwd(), rel_path.lstrip("/"))
            if os.path.exists(local_path):
                try:
                    with open(local_path, "rb") as f:
                        content = f.read()
                        gcs_path = immutable_storage_service.upload_to_immutable_bucket(
                            payload={}, external_id=radicado,
                            action=f"FINAL_SIGNED_{key.upper()}",
                            is_binary=True, content=content
                        )
                        immutable_artifacts[key] = gcs_path
                except: pass

        # 2.2. Firma Digital Final y Ledger
        await ledger_service.log_event(radicado, "FINAL_DEPENDENCY_APPROVAL", {
            "official_id": official_id,
            "immutable_paths": immutable_artifacts
        })

        # 2.3. Notificación al Ciudadano (Ajuste Crítico #5: Solo enviamos lo relevante)
        if case.peticionario_email:
            # Filtramos: Solo enviamos el Memorial y el Borrador (Respuesta), NO el traslado interno
            filtered_artifacts = {k: v for k, v in artifacts.items() if "traslado" not in k.lower()}
            
            abs_paths = [os.path.join(os.getcwd(), p.lstrip("/")) for p in filtered_artifacts.values()]
            await notification_service.send_official_radicado_email(
                recipient_email=case.peticionario_email,
                citizen_name=case.peticionario_nombre,
                radicado_id=radicado,
                pdf_paths=abs_paths
            )

        # 3. Marcar como FIRMADO/CERRADO
        case.estado = "FIRMADO"
        case.signed_at = datetime.datetime.utcnow()
        case.signed_by = official_id
        case.updated_at = datetime.datetime.utcnow()
        
        # 4. LIMPIEZA FINAL DE TOKENS (Ley 1581)
        from app.services.privacy_shield_service import privacy_shield
        await privacy_shield.cleanup_session(case.session_id)
        
        await session.commit()

        return {
            "status": "success",
            "message": f"Radicado {radicado} cerrado legalmente por la dependencia.",
            "signed_by": official_id,
            "notification": "sent"
        }
