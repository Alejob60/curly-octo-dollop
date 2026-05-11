from sqlalchemy import Column, String, JSON, DateTime, Integer, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.db_clients import Base
import uuid

class Dependency(Base):
    __tablename__ = "dependencias"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, index=True)
    nombre = Column(String(200), nullable=False)
    es_activa = Column(Boolean, default=True)

class PqrsType(Base):
    __tablename__ = "tipos_pqrs"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    sla_dias = Column(Integer, default=15)
    dias_respuesta = Column(Integer, default=15)

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    permisos = Column(JSON, default=[])

class User(Base):
    __tablename__ = "users"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(Text, nullable=True)
    full_name = Column(String(255))
    id_dependencia = Column(Integer, nullable=True)
    is_available = Column(Boolean, default=True)
    carga_actual = Column(Integer, default=0)
    capacidad_maxima = Column(Integer, default=10)
    especialidad = Column(String(100))
    role_id = Column(Integer, ForeignKey("roles.id"))
    role_name = Column(String(20), default="USER") # Para compatibilidad
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    role = relationship("Role")

class Radicado(Base):
    __tablename__ = "radicados"
    id = Column(Integer, primary_key=True, index=True)
    codigo_radicado = Column(String(50), unique=True, index=True)
    hash_seguridad = Column(String(255))
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_vencimiento = Column(DateTime(timezone=True))
    id_usuario_ciudadano = Column(String(50))
    id_dependencia = Column(Integer)
    id_tipo_pqrs = Column(Integer, ForeignKey("tipos_pqrs.id"))
    estado_actual = Column(String(50), default="RECIBIDO")
    id_funcionario_asignado = Column(String(50), ForeignKey("users.id"), nullable=True)
    
    tipo_pqrs = relationship("PqrsType")
    funcionario = relationship("User")

class Trazabilidad(Base):
    __tablename__ = "trazabilidad_logs"
    id = Column(Integer, primary_key=True, index=True)
    radicado_id = Column(Integer, ForeignKey("radicados.id"))
    estado_anterior = Column(String(50))
    estado_nuevo = Column(String(50), nullable=False)
    id_funcionario = Column(String(50))
    fecha_cambio = Column(DateTime(timezone=True), server_default=func.now())
    comentario = Column(Text)

class Asignacion(Base):
    __tablename__ = "asignaciones_ia"
    id = Column(Integer, primary_key=True, index=True)
    radicado_id = Column(Integer, ForeignKey("radicados.id"))
    funcionario_id = Column(Integer)
    nivel_complejidad = Column(String(20))
    sugerencia_ia_json = Column(Text)
    estado_revision = Column(String(50), default="SUGERIDO")

class AccionDependencia(Base):
    __tablename__ = "acciones_dependencia"
    id = Column(Integer, primary_key=True, index=True)
    radicado_id = Column(Integer, ForeignKey("radicados.id"))
    funcionario_id = Column(Integer)
    tipo_accion = Column(String(100))
    descripcion = Column(Text)
    resultado = Column(String(50))
    fecha_accion = Column(DateTime(timezone=True), server_default=func.now())

class EvidenciaBucket(Base):
    __tablename__ = "evidencias_bucket_logs"
    id = Column(Integer, primary_key=True, index=True)
    radicado_id = Column(Integer, ForeignKey("radicados.id"))
    gcs_uri = Column(String(500), nullable=False)
    tipo_documento = Column(String(100))
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now())

class AuditLedger(Base):
    __tablename__ = "audit_ledger_logs"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    registry_id = Column(String(50), index=True)
    action = Column(String(120))
    previous_hash = Column(Text)
    current_hash = Column(Text)
    payload = Column(JSON)
    transaction_id = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CitizenVault(Base):
    """Bóveda de Seguridad: Almacena PII cifrada (ARCH-2.1)"""
    __tablename__ = "citizen_vault"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    tipo_documento = Column(String(20))
    documento = Column(String(50), unique=True, index=True)
    nombres = Column(String(255))
    apellidos = Column(String(255))
    email = Column(String(150))
    celular = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SessionToken(Base):
    """Puente de Rehidratación: Mapeo temporal de Tokens vs Valores Reales"""
    __tablename__ = "session_tokens"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    token_key = Column(String(50)) # Ej: [NOMBRE_01]
    token_value = Column(Text)      # Ej: Alejandro Garzon
    expires_at = Column(DateTime(timezone=True))

class UserProfile(Base):
    """
    ARCH-1.1: Perfil de Usuario Persistente (Single Source of Truth).
    """
    __tablename__ = "user_profiles"

    cc = Column(String(20), primary_key=True, index=True)
    nombre_completo = Column(String(255), nullable=False)
    direccion_notificacion = Column(String(500))
    telefonos = Column(JSON, default=[]) 
    emails = Column(JSON, default=[])    
    historial_pqrs = Column(JSON, default=[]) 
    enfoque_diferencial = Column(JSON, default={})
    preferencias_canal = Column(String(50), default="chat")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CaseRegistry(Base):
    """
    Registro de Casos para el Dashboard de Gobernanza.
    """
    __tablename__ = "cases_registry"
    
    id = Column(Integer, primary_key=True, index=True)
    radicado = Column(String(50), unique=True, index=True)
    session_id = Column(String(100), index=True)
    user_cc = Column(String(20), ForeignKey("user_profiles.cc"))
    
    # Datos del ciudadano rehidratados (PII controlada)
    peticionario_nombre = Column(String(255))
    peticionario_documento = Column(String(50))
    peticionario_email = Column(String(150))
    
    # Datos del caso
    asunto = Column(String(255))
    tipo_solicitud = Column(String(100))
    dependencia_id = Column(String(10))
    dependencia_nombre = Column(String(200))
    
    # Estado del flujo
    estado = Column(String(50), default="INICIADO")
    current_phase = Column(String(50), default="fase_1_ingesta")
    completed_phases = Column(JSON, default=[])
    
    # Consentimiento y Firma Digital (Sprint 1.5)
    consent_granted = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime(timezone=True))
    consent_type = Column(String(100))
    consent_ip = Column(String(50))
    consent_signature_hash = Column(String(255)) # Huella digital del acuerdo
    
    # Calidad y enrutamiento (Sprint 3 Compliance)
    confidence_score = Column(Float, default=0.0)
    grounding_score = Column(Float, default=0.0)
    substance_score = Column(Float, default=0.0)
    structure_score = Column(Float, default=0.0)
    review_score = Column(Float, default=0.0)
    
    routing_queue = Column(String(50), default="human_only")
    urgencia_flag = Column(String(20), default="NORMAL")
    
    # Contenido generado
    hechos_extraidos = Column(Text)
    soporte_traslado = Column(Text)
    borrador_proyeccion = Column(Text)
    citas_verificables = Column(JSON, default=[])
    
    # Documentos y Auditoría
    pdf_paths = Column(JSON, default={})
    pdf_hashes = Column(JSON, default={})
    signed_at = Column(DateTime(timezone=True))
    signed_by = Column(String(100))
    
    # --- Interoperabilidad GovTech PR-01 ---
    orfeo_id = Column(String(100), unique=True)
    vencimiento_legal = Column(DateTime(timezone=True))
    alerta_vencimiento = Column(String(20), default="VERDE") # GREEN, YELLOW, RED, CRISIS
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("UserProfile", back_populates="cases")

class IntegrationConnector(Base):
    """
    Catálogo de conectores a sistemas legacy (Orfeo, SAP, SAUL, SIMIT, etc.)
    SPRINT 1: Motor de Integración Real (PR-01).
    """
    __tablename__ = "integration_connectors"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    system_type = Column(String(50), nullable=False) # orfeo, sap, saul, simit
    protocol = Column(String(50), nullable=False)    # rest, soap, database, sftp
    
    config = Column(JSON, nullable=False)            # URL, Auth refs, timeouts
    field_mapping = Column(JSON)                      # Mapeo legacy -> orbital
    
    sync_mode = Column(String(20), default="polling") # polling, webhook, manual
    sync_interval = Column(Integer, default=900)
    
    last_sync_at = Column(DateTime(timezone=True))
    last_sync_status = Column(String(50))
    health_status = Column(String(20), default="unknown")
    last_error = Column(Text)
    
    status = Column(String(20), default="active")    # active, inactive, error
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class DiagnosticLog(Base):
    """
    Log de diagnósticos pre-generación de documentos.
    Garantiza trazabilidad de la calidad documental.
    """
    __tablename__ = "diagnostic_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    radicado = Column(String(50), index=True)
    passed = Column(Boolean, default=False)
    results_json = Column(Text) # JSON stringificado con detalles del script
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FlowTelemetry(Base):
    """
    Telemetría de Flujo: Registra cada paso para análisis de productividad.
    """
    __tablename__ = "flow_telemetry"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    step_name = Column(String(100))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    context_snapshot = Column(JSON)
    integrity_hash = Column(String(64))
    processing_time = Column(Float) # Segundos tomados por el paso

UserProfile.cases = relationship("CaseRegistry", back_populates="user")
