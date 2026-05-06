from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

class GovDocsPayload(BaseModel):
    """Esquema Estándar de Orbital Prime (IBM Sterling Inspired)"""
    external_id: str = Field(..., description="ID original del sistema de origen")
    source_system: str = Field(..., description="Nombre del sistema (SAP, ORFEO, BIGQUERY)")
    citizen_name: str
    citizen_id: str
    citizen_email: EmailStr
    content: str
    category: Optional[str] = "PETICIÓN"
    metadata: Dict[str, Any] = {}

class RawIngestionResponse(BaseModel):
    task_id: str
    status: str = "INGESTED"
    ingested_at: datetime
