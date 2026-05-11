from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

class ExtractionResult(BaseModel):
    """Esquema estricto para la respuesta de la IA (V65.5)"""
    mensaje_ia: str = Field(..., description="Respuesta fluida y amable para el ciudadano.")
    tipo_solicitud: str = Field(..., description="Categoría legal de la solicitud.")
    tipo_solicitante: str = Field(..., description="Persona Natural o Jurídica.")
    tipo_documento: Optional[str] = None
    documento: Optional[str] = None
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    departamento: str = Field(default="Valle del Cauca")
    municipio: str = Field(default="Cali")
    direccion: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    asunto: str = Field(..., description="Resumen técnico para el radicado.")

class VerifiableCitation(BaseModel):
    citacion_formato: str = Field(..., description="Ej: Ley 1755 de 2015 o Dec 3075 de 1997")
    articulo: str = Field(..., description="Número del artículo citado")
    ente_emisor: str = Field(..., description="Entidad que emitió la norma")
    texto_relevante: str = Field(..., description="Fragmento de la norma aplicado")

class LegalAnalysisResult(BaseModel):
    """Esquema para el análisis profundo de background (V65.12 Diamond)"""
    asunto: str = Field(..., description="Resumen técnico y formal de la solicitud (máx 15 palabras).")
    hechos_extraidos: str = Field(..., description="Relato cronológico y técnico detallado de los hechos. Mínimo 100 palabras.")
    borrador_proyeccion: str = Field(..., description="Texto jurídico COMPLETO y DE FONDO. Debe incluir: Antecedentes, Análisis Normativo (usando RAG) y Resolución Concreta. PROHIBIDO USAR FRASES GENÉRICAS.")
    citas_verificables: List[VerifiableCitation] = Field(..., description="Lista de al menos 2 citas legales reales extraídas del contexto RAG provisto.")
