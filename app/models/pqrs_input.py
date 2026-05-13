from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, Dict, Any, List
from datetime import date
import re

class PQRSInputSchema(BaseModel):
    """
    💎 [V65.13 Diamond] Contrato de Entrada Unificada.
    Normaliza datos de Frontend, API Interna y Migraciones Batch.
    """
    model_config = {"extra": "allow", "strict": False}

    # 🔑 Identificación única (idempotencia)
    idempotency_key: Optional[str] = None
    
    # 📝 Datos del peticionario
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    identificacion: Optional[str] = None
    entidad: Optional[str] = None
    email: Optional[str] = None
    celular: Optional[str] = None
    direccion: Optional[str] = None

    # 📄 Contenido de la solicitud
    tipo_pqrs: Optional[str] = Field(None, pattern="^(PQRS|PETICION|QUEJA|RECLAMO|SUGERENCIA|DENUNCIA|CAPACITACION)$")
    asunto: str = Field(..., min_length=5)
    descripcion: str = Field(..., min_length=10)
    fecha_solicitada: Optional[str] = None
    adjuntos: Optional[List[str]] = None

    # 🌐 Metadata de origen
    source: Optional[str] = Field("api", pattern="^(frontend|internal_api|migration|batch|api)$")
    priority: Optional[str] = Field("NORMAL", pattern="^(ALTA|MEDIA|NORMAL|BAJA)$")

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, values):
        if not isinstance(values, dict): return values
        
        # Mapeo de campos alternativos (Legacy / Frontend)
        if "user_data" in values:
            values.update(values.pop("user_data"))
        if "content" in values:
            values["descripcion"] = values.pop("content")
        if "message" in values:
            values["descripcion"] = values.get("descripcion") or values.pop("message")
        if "subject" in values:
            values["asunto"] = values.pop("subject")
            
        return values

    @field_validator("identificacion")
    @classmethod
    def sanitize_id(cls, v):
        if v:
            v = re.sub(r"[^0-9A-Za-z\-]", "", str(v))
            if len(v) < 5: raise ValueError("Identificación muy corta")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Email con formato inválido")
        return v
