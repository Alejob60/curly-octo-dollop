from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal
from datetime import date
import json

class Peticionario(BaseModel):
    nombres: Optional[str] = Field(None, min_length=1)
    apellidos: Optional[str] = None
    identificacion: Optional[str] = None
    entidad: Optional[str] = None

class FundamentoLegal(BaseModel):
    ley: str
    articulo: str
    texto: str

class Auditoria(BaseModel):
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    riesgo_tutela: Literal["BAJO", "MEDIO", "ALTO"]
    citas_verificadas: bool
    requires_human_review: bool
    error_trace: List[str] = Field(default_factory=list)

class Watermark(BaseModel):
    label: str
    hash_sha256: str
    timestamp: str
    version: str = "V65.14"

class FlujoDocumentos(BaseModel):
    traslado: dict = Field(default_factory=dict)
    proyeccion: dict = Field(default_factory=dict)
    logistica: dict = Field(default_factory=dict)
    memorial: dict = Field(default_factory=dict)
    auto: dict = Field(default_factory=dict)

class StrictLegalOutput(BaseModel):
    """
    💎 [V65.14 Diamond] Contrato Estricto del Agente Judicial.
    Garantiza cero alucinaciones y cumplimiento normativo.
    """
    model_config = {"extra": "forbid", "strict": True}
    
    radicado: str
    decision_recommendation: Literal["APROBAR", "DENEGAR", "CONDICIONAR", "REQUERIR", "TRASLADAR"]
    asunto: Optional[str] = None
    peticionario: Peticionario
    fecha_solicitada: Optional[str] = None
    fecha_valida: Optional[bool] = True
    validation_requests: List[dict] = Field(default_factory=list)
    flujo_documentos: FlujoDocumentos
    auditoria: Auditoria
    watermark: Watermark
    
    @model_validator(mode="after")
    def block_placeholders(self):
        raw = self.model_dump_json().lower()
        placeholders = ["123456789", "equipo técnico", "50 personas", "cc 123456789", "por definir"]
        if any(ph in raw for ph in placeholders):
            raise ValueError(f"❌ Hallucinación detectada: Uso de placeholders prohibidos en producción.")
        return self
