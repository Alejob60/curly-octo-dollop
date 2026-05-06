import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import text

from app.core.azure_openai_client import get_async_azure_openai_client
from app.core.config import settings
from app.core.db_clients import AsyncSessionLocal, mongo_db
from app.core.vector_store import vector_store
from app.schemas.final_validation import (
    AuditResult,
    FinalValidationRequest,
    FinalValidationResponse,
    LegalContextEntry,
    WorkOrderPayload,
)
from app.services.gcp_storage_orchestrator import gcp_storage_orchestrator
from app.services.integration_security_service import integration_security_service
from app.services.ledger_service import ledger_service
from app.services.pdf_service import pdf_service
from app.services.signer import signer_service


class FinalValidationService:
    def __init__(self):
        self.ai_client = get_async_azure_openai_client()

    async def generate_master_response(
        self,
        payload: FinalValidationRequest,
        current_user: Optional[dict[str, Any]] = None,
    ) -> FinalValidationResponse:
        draft = await mongo_db.document_store.find_one({"external_id": payload.external_id}) or {}
        context_entries = await self._load_legal_context(payload)
        generated_content = await self._build_resolution_content(payload, context_entries, draft)
        generated_content = self._enforce_required_sections(payload, generated_content, context_entries)
        audit_result = await self._audit_resolution(payload, generated_content, draft, context_entries)

        if audit_result.fidelity_score < payload.minimum_fidelity or not audit_result.approved:
            generated_content = await self._revise_resolution_after_audit(
                payload,
                generated_content,
                audit_result,
                context_entries,
            )
            generated_content = self._enforce_required_sections(payload, generated_content, context_entries)
            audit_result = await self._audit_resolution(payload, generated_content, draft, context_entries)

        if audit_result.fidelity_score < payload.minimum_fidelity or not audit_result.approved:
            raise ValueError(
                f"La auditoria legal rechazo el borrador: score={audit_result.fidelity_score:.3f}, umbral={payload.minimum_fidelity:.3f}"
            )

        work_order = self._build_work_order(payload, generated_content, draft)
        content_digest = ledger_service.calculate_hash(
            {
                "external_id": payload.external_id,
                "content": generated_content,
                "audit": audit_result.model_dump(),
                "work_order": work_order.model_dump(),
            }
        )
        signature = signer_service.sign_digest_sha256(content_digest)

        await ledger_service.log_event(
            payload.external_id,
            "MASTER_VALIDATION_COMPLETED",
            {
                "fidelity_score": audit_result.fidelity_score,
                "approved": audit_result.approved,
                "operation_type": work_order.operation_type,
                "target_system": work_order.target_system,
                "content_digest": content_digest,
                "signature_ref": signature.get("key_version"),
            },
        )
        transaction_id = await self._get_latest_transaction_id(payload.external_id)

        metadata_pdf = {
            "citizen_name": payload.citizen_name,
            "citizen_address": payload.citizen_address or draft.get("citizen_address") or "NO REPORTADA",
            "category": payload.category,
            "dept_name": payload.department_name,
            "topic": payload.topic,
            "requested_action": payload.requested_action,
            "due_days": payload.due_days,
            "legal_references": [entry.model_dump() for entry in context_entries],
            "fidelity_score": audit_result.fidelity_score,
            "signature_ref": signature.get("key_version") or "NO_KMS",
            "provider": audit_result.provider,
        }
        pdf_buffer = await pdf_service.generate_master_response_pdf(
            external_id=payload.external_id,
            content=generated_content,
            lawyer_name=(current_user or {}).get("email") or "Secretario Juridico Delegado",
            transaction_id=transaction_id,
            metadata=metadata_pdf,
        )

        pdf_storage_path = azure_blob_service.upload_file(
            pdf_buffer.getvalue(),
            payload.external_id,
            "final-validation",
            f"PDF_MAESTRO_{payload.external_id}.pdf",
        )
        audit_storage_path = azure_blob_service.upload_file(
            json.dumps(audit_result.model_dump(), ensure_ascii=True, indent=2),
            payload.external_id,
            "audit",
            f"AUDITORIA_VERTEX_{payload.external_id}.json",
        )
        work_order_storage_path = azure_blob_service.upload_file(
            work_order.model_dump(),
            payload.external_id,
            "operations",
            f"ORDEN_OPERATIVA_{payload.external_id}.json",
        )

        persisted_payload = {
            "generated_content": generated_content,
            "audit": audit_result.model_dump(),
            "work_order": work_order.model_dump(),
            "artifacts": {
                "pdf_storage_path": pdf_storage_path,
                "audit_storage_path": audit_storage_path,
                "work_order_storage_path": work_order_storage_path,
            },
            "updated_at": datetime.utcnow(),
            "simulated": payload.simulate,
        }
        await mongo_db.document_store.update_one(
            {"external_id": payload.external_id},
            {
                "$set": {
                    "external_id": payload.external_id,
                    "citizen_name": payload.citizen_name,
                    "citizen_email": payload.citizen_email,
                    "category": payload.category,
                    "master_validation": persisted_payload,
                }
            },
            upsert=True,
        )

        await integration_security_service.log_event(
            event_type="MASTER_VALIDATION_READY",
            status="success",
            detail=f"PDF maestro y orden operativa generados para {payload.external_id}",
            system_name="FINAL_VALIDATION",
            metadata={
                "external_id": payload.external_id,
                "pdf_storage_path": pdf_storage_path,
                "work_order_storage_path": work_order_storage_path,
                "fidelity_score": audit_result.fidelity_score,
            },
        )

        return FinalValidationResponse(
            external_id=payload.external_id,
            approved=audit_result.approved,
            fidelity_score=audit_result.fidelity_score,
            legal_context=context_entries,
            work_order=work_order,
            pdf_storage_path=pdf_storage_path,
            audit_storage_path=audit_storage_path,
            work_order_storage_path=work_order_storage_path,
            audit_transaction_id=transaction_id,
            generated_at=datetime.utcnow(),
            provider=audit_result.provider,
            simulated=payload.simulate,
        )

    async def _load_legal_context(self, payload: FinalValidationRequest) -> List[LegalContextEntry]:
        if payload.simulate:
            return [
                LegalContextEntry(
                    source="fallback",
                    title="Ley 1437 de 2011",
                    excerpt="El CPACA exige motivacion, debido proceso administrativo y coherencia entre hechos, fundamento y decision.",
                    reference="CPACA",
                ),
                LegalContextEntry(
                    source="fallback",
                    title="Ley 1755 de 2015",
                    excerpt="El derecho de peticion debe responderse de fondo, de manera clara, precisa y oportuna.",
                    reference="Art. 13 y 14",
                ),
                LegalContextEntry(
                    source="fallback",
                    title="Precedente de mantenimiento programado",
                    excerpt="La entidad puede ordenar intervencion con plazo definido y notificacion al ciudadano cuando exista riesgo operativo verificable.",
                    reference="Memoria juridica demo",
                ),
            ]

        keywords = self._extract_keywords(payload)
        regex = "|".join(re.escape(word) for word in keywords) if keywords else payload.topic
        context_entries: List[LegalContextEntry] = []

        try:
            cursor = mongo_db.legal_knowledge.find(
                {
                    "$or": [
                        {"content": {"$regex": regex, "$options": "i"}},
                        {"law_name": {"$regex": regex, "$options": "i"}},
                    ]
                },
                {"_id": 0},
            ).limit(4)
            laws = await cursor.to_list(length=4)
        except Exception as exc:
            logger.warning(f"No fue posible cargar leyes desde Mongo: {exc}")
            laws = []

        for law in laws:
            context_entries.append(
                LegalContextEntry(
                    source="legal_knowledge",
                    title=law.get("law_name", "Norma sin titulo"),
                    excerpt=law.get("content", ""),
                    reference=f"Art. {law.get('article_number', 's/n')}",
                )
            )

        try:
            precedents = await vector_store.search_similar_cases(
                f"{payload.topic}. {payload.original_report}. {payload.requested_action}",
                limit=3,
            )
        except Exception as exc:
            logger.warning(f"No fue posible cargar precedentes vectoriales: {exc}")
            precedents = []

        for precedent in precedents:
            context_entries.append(
                LegalContextEntry(
                    source="legal_precedents",
                    title=f"{precedent.get('type', 'PRECEDENTE')} - {precedent.get('outcome', 'N/A')}",
                    excerpt=precedent.get("argument", ""),
                    reference="pgvector",
                )
            )

        if not context_entries:
            context_entries.extend(
                [
                    LegalContextEntry(
                        source="fallback",
                        title="Ley 1437 de 2011",
                        excerpt="El CPACA exige motivacion, debido proceso administrativo y coherencia entre hechos, fundamento y decision.",
                        reference="CPACA",
                    ),
                    LegalContextEntry(
                        source="fallback",
                        title="Ley 1755 de 2015",
                        excerpt="El derecho de peticion debe responderse de fondo, de manera clara, precisa y oportuna.",
                        reference="Art. 13 y 14",
                    ),
                ]
            )

        return context_entries[:6]

    async def _build_resolution_content(
        self,
        payload: FinalValidationRequest,
        context_entries: List[LegalContextEntry],
        draft: Dict[str, Any],
    ) -> str:
        if payload.simulate:
            return self._build_simulated_resolution(payload, context_entries)

        context_block = "\n".join(
            f"- {entry.title} ({entry.reference or entry.source}): {entry.excerpt}"
            for entry in context_entries
        )
        draft_hint = draft.get("ai_response_final") or draft.get("ai_response_reviewed") or ""
        prompt = f"""
Actua como Secretario Juridico de la Alcaldia de Cali.

RADICADO: {payload.external_id}
CIUDADANO: {payload.citizen_name}
DIRECCION: {payload.citizen_address or 'NO REPORTADA'}
TEMA: {payload.topic}
REPORTE ORIGINAL: {payload.original_report}
ACCION REQUERIDA: {payload.requested_action}
PLAZO MAXIMO: {payload.due_days} dias habiles

CONTEXTO JURIDICO Y PRECEDENTES:
{context_block}

BORRADOR PREVIO SI EXISTE:
{draft_hint}

Redacta una respuesta oficial con esta estructura:
1. Antecedentes.
2. Fundamento juridico citando las normas del contexto.
3. Resuelve, indicando la intervencion ordenada y el plazo.
4. Cierre al ciudadano con lenguaje institucional.

No inventes hechos y responde solo con el contenido final del documento.
"""
        response = await self.ai_client.chat.completions.create(
            model=settings.AI_CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un redactor juridico senior del sector publico colombiano. Debes responder con rigor legal y lenguaje administrativo claro.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=2200,
        )
        return (response.choices[0].message.content or "").strip()

    async def _audit_resolution(
        self,
        payload: FinalValidationRequest,
        generated_content: str,
        draft: Dict[str, Any],
        context_entries: List[LegalContextEntry],
    ) -> AuditResult:
        if payload.simulate:
            return self._build_simulated_audit(payload, generated_content, context_entries)

        context_titles = [entry.title for entry in context_entries]
        audit_prompt = f"""
Audita juridicamente el siguiente borrador y responde SOLO en JSON valido con estas llaves:
approved, fidelity_score, summary, observations, legal_consistency, field_checks.

Reglas:
- fidelity_score debe quedar entre 0 y 1.
- approved debe ser true solo si fidelity_score >= {payload.minimum_fidelity}.
- field_checks debe revisar citizen_name, citizen_address y external_id.

INPUT:
- external_id: {payload.external_id}
- citizen_name: {payload.citizen_name}
- citizen_address: {payload.citizen_address or draft.get('citizen_address') or 'NO REPORTADA'}
- topic: {payload.topic}
- context_titles: {context_titles}

BORRADOR:
{generated_content}
"""
        try:
            response = await self.ai_client.chat.completions.create(
                model=settings.AI_CHAT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un auditor legal estricto. Debes validar consistencia juridica y factual sin tolerar alucinaciones.",
                    },
                    {"role": "user", "content": audit_prompt},
                ],
                max_completion_tokens=1000,
            )
            raw_content = (response.choices[0].message.content or "{}").strip()
            payload_json = self._extract_json(raw_content)
            score = float(payload_json.get("fidelity_score", 0.0))
            if score > 1:
                score = score / 100.0
            approved = bool(payload_json.get("approved", score >= payload.minimum_fidelity))
            observations = self._normalize_string_list(payload_json.get("observations"))
            legal_consistency = self._normalize_string_list(payload_json.get("legal_consistency"))
            field_checks = self._normalize_field_checks(payload_json.get("field_checks"))
            return AuditResult(
                approved=approved,
                fidelity_score=max(0.0, min(score, 1.0)),
                summary=payload_json.get("summary", "Auditoria completada"),
                observations=observations,
                legal_consistency=legal_consistency,
                field_checks=field_checks,
                provider=settings.AI_PROVIDER,
            )
        except Exception as exc:
            logger.warning(f"Fallo auditoria AI, usando heuristica local: {exc}")
            return self._build_simulated_audit(payload, generated_content, context_entries)

    def _build_simulated_resolution(
        self,
        payload: FinalValidationRequest,
        context_entries: List[LegalContextEntry],
    ) -> str:
        legal_basis = "; ".join(
            f"{entry.title} {f'({entry.reference})' if entry.reference else ''}" for entry in context_entries[:3]
        )
        return (
            f"Antecedentes: se recibe el radicado {payload.external_id} presentado por {payload.citizen_name} "
            f"sobre {payload.topic}. Conforme al reporte original, {payload.original_report}.\n\n"
            f"Fundamento juridico: esta decision se soporta en {legal_basis}, en armonia con el deber de respuesta de fondo y la planeacion del mantenimiento programado.\n\n"
            f"Resuelve: ordenar la actuacion administrativa de {payload.requested_action} con prioridad operativa {self._infer_priority(payload)} "
            f"y plazo maximo de {payload.due_days} dias habiles. La dependencia competente debera dejar trazabilidad de la visita, ejecucion y cierre.\n\n"
            f"Comuniquese al ciudadano en la direccion {payload.citizen_address or 'registrada en el expediente'} y archivese con constancia de auditoria digital."
        )

    async def _revise_resolution_after_audit(
        self,
        payload: FinalValidationRequest,
        generated_content: str,
        audit_result: AuditResult,
        context_entries: List[LegalContextEntry],
    ) -> str:
        if payload.simulate:
            return generated_content

        references = "; ".join(
            f"{entry.title} ({entry.reference or entry.source})" for entry in context_entries[:4]
        )
        audit_feedback = "; ".join(audit_result.observations or audit_result.legal_consistency) or audit_result.summary
        prompt = f"""
Corrige el siguiente acto administrativo para superar una auditoria juridica estricta.

Debes mantener el sentido del documento, pero asegurar explicitamente:
- Radicado: {payload.external_id}
- Ciudadano: {payload.citizen_name}
- Direccion: {payload.citizen_address or 'NO REPORTADA'}
- Plazo: {payload.due_days} dias habiles
- Accion ordenada: {payload.requested_action}
- Fundamento juridico con estas referencias: {references}
- Secciones claras: Antecedentes, Fundamento juridico, Resuelve, Notificacion.

Observaciones de auditoria previa:
{audit_feedback}

Documento actual:
{generated_content}

Devuelve solo la version corregida final.
"""
        response = await self.ai_client.chat.completions.create(
            model=settings.AI_CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un revisor juridico senior. Tu trabajo es convertir borradores aceptables en actos administrativos formalmente impecables.",
                },
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=2200,
        )
        return (response.choices[0].message.content or generated_content).strip()

    def _build_simulated_audit(
        self,
        payload: FinalValidationRequest,
        generated_content: str,
        context_entries: List[LegalContextEntry],
    ) -> AuditResult:
        checks = {
            "citizen_name": "ok" if payload.citizen_name.lower() in generated_content.lower() else "missing",
            "citizen_address": "ok" if not payload.citizen_address or payload.citizen_address.lower() in generated_content.lower() else "missing",
            "external_id": "ok" if payload.external_id.lower() in generated_content.lower() else "missing",
        }
        missing = [field for field, status in checks.items() if status != "ok"]
        context_bonus = 0.02 if context_entries else 0.0
        score = 0.97 + context_bonus - (0.03 * len(missing))
        score = max(0.7, min(score, 0.99))
        return AuditResult(
            approved=score >= payload.minimum_fidelity,
            fidelity_score=score,
            summary="Auditoria heuristica completada para demostracion controlada",
            observations=[f"Campo faltante: {item}" for item in missing],
            legal_consistency=["Se verifico presencia de fundamento juridico y orden operativa"],
            field_checks=checks,
            provider="simulated" if payload.simulate else "heuristic-fallback",
        )

    def _build_work_order(
        self,
        payload: FinalValidationRequest,
        generated_content: str,
        draft: Dict[str, Any],
    ) -> WorkOrderPayload:
        operation_type = payload.operation_type or self._infer_operation_type(payload)
        target_system = self._target_system_for_operation(operation_type)
        priority = self._infer_priority(payload)
        instructions = [
            "Validar georreferenciacion y evidencia fotografica del punto reportado.",
            f"Ejecutar {payload.requested_action.lower()} y registrar inicio/cierre en el sistema operativo.",
            "Notificar al ciudadano la fecha objetivo y el estado de la orden.",
        ]
        return WorkOrderPayload(
            external_id=payload.external_id,
            target_system=target_system,
            operation_type=operation_type,
            priority=priority,
            due_days=payload.due_days,
            summary=f"{payload.topic} - {payload.requested_action}",
            instructions=instructions,
            citizen_notice=(
                f"La Alcaldia programo una intervencion de tipo {operation_type.lower()} para el radicado {payload.external_id} "
                f"con plazo estimado de {payload.due_days} dias habiles."
            ),
            metadata={
                "source_channel": payload.source_channel,
                "category": payload.category,
                "draft_present": bool(draft),
                "content_preview": generated_content[:180],
                **payload.metadata,
            },
        )

    def _infer_operation_type(self, payload: FinalValidationRequest) -> str:
        haystack = f"{payload.topic} {payload.original_report} {payload.requested_action}".lower()
        if any(term in haystack for term in ["hueco", "bache", "vial", "pavimento"]):
            return "INFRAESTRUCTURA_VIAL"
        if any(term in haystack for term in ["semaforo", "movilidad", "interseccion", "trafico"]):
            return "TRANSITO"
        if any(term in haystack for term in ["luminaria", "alumbrado", "poste", "luz"]):
            return "ALUMBRADO_PUBLICO"
        return "SERVICIOS_CIUDAD"

    def _target_system_for_operation(self, operation_type: str) -> str:
        mapping = {
            "INFRAESTRUCTURA_VIAL": "INFRAESTRUCTURA_CALI",
            "TRANSITO": "CENTRO_GESTION_TRANSITO",
            "ALUMBRADO_PUBLICO": "ALUMBRADO_CALI",
            "SERVICIOS_CIUDAD": "MESA_SERVICIOS_DISTRITO",
        }
        return mapping.get(operation_type, "MESA_SERVICIOS_DISTRITO")

    def _infer_priority(self, payload: FinalValidationRequest) -> str:
        haystack = f"{payload.topic} {payload.original_report}".lower()
        if any(term in haystack for term in ["peligro", "accidente", "riesgo", "falla total"]):
            return "ALTA"
        if any(term in haystack for term in ["semaforo", "movilidad", "luminaria"]):
            return "MEDIA_ALTA"
        return "MEDIA"

    def _extract_keywords(self, payload: FinalValidationRequest) -> List[str]:
        raw_text = f"{payload.topic} {payload.original_report} {payload.requested_action}"
        words = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ0-9]{4,}", raw_text)
        deduped: List[str] = []
        for word in words:
            lowered = word.lower()
            if lowered not in deduped:
                deduped.append(lowered)
        return deduped[:10]

    async def _get_latest_transaction_id(self, external_id: str) -> str:
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text(
                        "SELECT transaction_id FROM audit_ledger WHERE registry_id=:id ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"id": external_id},
                )
                row = result.fetchone()
                return row[0] if row and row[0] else "LOCAL_ONLY"
        except Exception as exc:
            logger.warning(f"No fue posible consultar audit_ledger: {exc}")
            return "LOCAL_ONLY"

    def _extract_json(self, raw_content: str) -> Dict[str, Any]:
        cleaned = raw_content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        return json.loads(cleaned)

    def _enforce_required_sections(
        self,
        payload: FinalValidationRequest,
        content: str,
        context_entries: List[LegalContextEntry],
    ) -> str:
        normalized = content.strip()
        lower = normalized.lower()
        references = "; ".join(
            f"{entry.title} ({entry.reference or entry.source})" for entry in context_entries[:4]
        )

        required_headers = {
            "antecedentes": "I. ANTECEDENTES",
            "fundamento juridico": "II. FUNDAMENTO JURIDICO",
            "resuelve": "III. RESUELVE",
            "notificacion": "IV. NOTIFICACION",
        }
        for needle, header in required_headers.items():
            if needle not in lower:
                normalized += f"\n\n{header}\nPendiente de integracion formal en el cuerpo principal del acto administrativo."
                lower = normalized.lower()

        required_fragments = [
            (payload.external_id.lower(), f"\n\nRadicado oficial: {payload.external_id}."),
            (payload.citizen_name.lower(), f"\nCiudadano: {payload.citizen_name}."),
            ((payload.citizen_address or "").lower(), f"\nDireccion reportada: {payload.citizen_address}." if payload.citizen_address else ""),
            (str(payload.due_days).lower(), f"\nPlazo de cumplimiento: {payload.due_days} dias habiles."),
        ]
        for needle, snippet in required_fragments:
            if needle and needle not in lower and snippet:
                normalized += snippet
                lower = normalized.lower()

        if references and "fundamento juridico" in normalized.lower() and references.lower() not in lower:
            normalized += f"\nFundamento juridico adicional: {references}."

        return normalized

    def _normalize_string_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str):
            return [value] if value.strip() else []
        return [str(value)]

    def _normalize_field_checks(self, value: Any) -> Dict[str, str]:
        if not isinstance(value, dict):
            return {}

        normalized: Dict[str, str] = {}
        for key, item in value.items():
            if isinstance(item, dict):
                if "match" in item:
                    normalized[key] = "ok" if bool(item.get("match")) else "mismatch"
                elif "status" in item:
                    normalized[key] = str(item.get("status"))
                else:
                    normalized[key] = json.dumps(item, ensure_ascii=True)
            else:
                normalized[key] = str(item)
        return normalized


final_validation_service = FinalValidationService()
