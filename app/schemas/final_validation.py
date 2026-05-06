from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class FinalValidationRequest(BaseModel):
    external_id: str = Field(..., description="Radicado oficial a resolver")
    citizen_name: str = Field(..., description="Nombre del ciudadano reportante")
    citizen_email: Optional[EmailStr] = Field(default=None)
    citizen_address: Optional[str] = Field(default=None)
    topic: str = Field(..., description="Tema principal de la PQRSD")
    original_report: str = Field(..., description="Texto original del reporte ciudadano o del sensor")
    requested_action: str = Field(..., description="Accion esperada por la entidad")
    category: str = Field(default="PETICION")
    department_name: str = Field(default="SECRETARIA JURIDICA MUNICIPAL")
    operation_type: Optional[str] = Field(default=None, description="INFRAESTRUCTURA, TRANSITO, ALUMBRADO, etc.")
    due_days: int = Field(default=5, ge=1, le=30)
    minimum_fidelity: float = Field(default=0.95, ge=0.5, le=1.0)
    source_channel: str = Field(default="ORBITAL_AGENT")
    simulate: bool = Field(default=False, description="Si es true, evita dependencias externas y usa una respuesta deterministica")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LegalContextEntry(BaseModel):
    source: str
    title: str
    excerpt: str
    reference: Optional[str] = None


class AuditResult(BaseModel):
    approved: bool
    fidelity_score: float
    summary: str
    observations: List[str] = Field(default_factory=list)
    legal_consistency: List[str] = Field(default_factory=list)
    field_checks: Dict[str, str] = Field(default_factory=dict)
    provider: str


class WorkOrderPayload(BaseModel):
    external_id: str
    target_system: str
    operation_type: str
    priority: str
    due_days: int
    summary: str
    instructions: List[str] = Field(default_factory=list)
    citizen_notice: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FinalValidationResponse(BaseModel):
    external_id: str
    approved: bool
    fidelity_score: float
    legal_context: List[LegalContextEntry]
    work_order: WorkOrderPayload
    pdf_storage_path: str
    audit_storage_path: str
    work_order_storage_path: str
    audit_transaction_id: str
    generated_at: datetime
    provider: str
    simulated: bool
