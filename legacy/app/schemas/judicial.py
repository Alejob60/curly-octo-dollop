from pydantic import BaseModel, Field
from typing import List, Optional


class ClaimItem(BaseModel):
    concept: str = Field(..., description="Concepto de la pretension")
    amount: Optional[float] = Field(default=None, description="Valor numerico detectado")
    currency: str = Field(default="COP", description="Moneda detectada")


class PartyInfo(BaseModel):
    role: str = Field(..., description="Rol procesal")
    name: str = Field(..., description="Nombre de la parte")
    id_number: Optional[str] = Field(default=None, description="Documento de identidad si existe")


class JudicialParseResponse(BaseModel):
    summary: str
    pretensiones: List[ClaimItem]
    partes: List[PartyInfo]
    pruebas_aportadas: List[str]
    probabilidad_exito: float = Field(..., ge=0.0, le=1.0)
    precedentes_similares: List[dict]
