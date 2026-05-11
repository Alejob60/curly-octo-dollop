from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Forzamos recarga del .env para evitar variables "pegadas" en el shell
load_dotenv(override=True)

class Settings(BaseSettings):
    # === 🚀 ENTORNOS Y PUERTOS ===
    APP_NAME: str = "Orbital Prime GovDocs"
    ENV: str = os.getenv("ENV", "development")
    API_V1_STR: str = "/api/v1"
    
    # === 🐘 BASES DE DATOS (Single Source of Truth) ===
    # PostgreSQL (Bóveda Identidad)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/orbital_prime")
    
    @property
    def get_database_url(self) -> str:
        return self.DATABASE_URL

    # Valkey/Redis (Bóveda Estados Cards)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    VALKEY_URL: Optional[str] = os.getenv("VALKEY_URL")
    VALKEY_HOST: str = os.getenv("VALKEY_HOST", "localhost")
    VALKEY_PORT: int = int(os.getenv("VALKEY_PORT", 6379))
    
    # MongoDB Atlas (RAG Legal)
    MONGODB_PROVIDER: str = os.getenv("MONGODB_PROVIDER", "atlas").lower()
    MONGODB_ATLAS_URI: Optional[str] = os.getenv("MONGODB_ATLAS_URI")
    MONGO_URL: str = os.getenv("MONGODB_ATLAS_URI", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGODB_ATLAS_DB", "orbital_prime_atlas")
    
    # === 🧠 INTELIGENCIA GCP (Vertex AI) ===
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "misybot-ai-beta")
    GCP_LOCATION: str = os.getenv("GCP_LOCATION", "us-central1")
    VERTEX_MODEL_NAME: str = os.getenv("VERTEX_MODEL_NAME", "gemini-2.5-flash")
    VERTEX_API_KEY: Optional[str] = os.getenv("VERTEX_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    NVIDIA_NIMS_API_KEY: Optional[str] = os.getenv("NVIDIA_NIMS_API_KEY")

    # Unified AI Interface
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "vertex")
    AI_CHAT_MODEL: str = os.getenv("AI_CHAT_MODEL", "gemini-2.5-flash")
    AI_EMBEDDING_MODEL: str = os.getenv("AI_EMBEDDING_MODEL", "text-embedding-004")
    AI_EMBEDDING_DIMENSIONS: int = int(os.getenv("AI_EMBEDDING_DIMENSIONS", "768"))

    # === 🛡️ SEGURIDAD Y PRIVACIDAD (Habeas Data) ===
    JWT_SECRET: str = os.getenv("JWT_SECRET", "orbital-prime-sovereign-secret")
    INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "orbital-prime-dev-key-2026")
    DATABASE_ENCRYPTION_KEY: Optional[str] = os.getenv("DATABASE_ENCRYPTION_KEY")
    GCP_TENANT_PREFIX: str = os.getenv("GCP_TENANT_PREFIX", "misybot-cali")
    
    # GCP KMS (Hardware Security Module)
    GCP_KMS_LOCATION: str = os.getenv("GCP_KMS_LOCATION", "us-central1")
    GCP_KMS_KEYRING: str = os.getenv("GCP_KMS_KEYRING", "orbital-keyring")
    GCP_KMS_KEY: str = os.getenv("GCP_KMS_KEY", "orbital-prime-key")
    GCP_KMS_KEY_ID: str = os.getenv("GCP_KMS_KEY_ID", "orbital-prime-key")
    GCP_KMS_KEY_NAME: Optional[str] = os.getenv("GCP_KMS_KEY_NAME")
    
    # === 🏛️ GOBERNANZA Y LEDGER (GCP-WORM) ===
    LEDGER_PROVIDER: str = os.getenv("LEDGER_PROVIDER", "gcp")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "orbital-prime-docs")
    GCP_IMMUTABLE_BUCKET: str = os.getenv("GCP_IMMUTABLE_BUCKET", "misybot-cali-immutable-ledger")
    GCP_WORM_RETENTION_DAYS: int = 7300 # 20 años
    VERIFY_BASE_URL: str = os.getenv("VERIFY_BASE_URL", "http://localhost:8000/verify")

    # === 📡 LEGACY BRIDGES (Interoperability PR-01) ===
    ORFEO_BRIDGE_URL: str = os.getenv("ORFEO_BRIDGE_URL", "https://orfeo-bridge.internal.cali.gov.co/v1")
    SAUL_BRIDGE_URL: str = os.getenv("SAUL_BRIDGE_URL", "https://saul-bridge.internal.cali.gov.co/v1")
    SAP_BRIDGE_URL: str = os.getenv("SAP_BRIDGE_URL", "https://sap-bridge.internal.cali.gov.co/v1")
    LEGACY_API_TIMEOUT: int = int(os.getenv("LEGACY_API_TIMEOUT", 10))
    LEGACY_BRIDGE_TOKEN: str = os.getenv("LEGACY_BRIDGE_TOKEN", "orbital-bridge-secret-2026")

    # GCP Pub/Sub (Ingesta Masiva)
    GCP_PUBSUB_PROJECT_ID: str = os.getenv("GCP_PUBSUB_PROJECT_ID", "misybot-ai-beta")
    GCP_PUBSUB_TOPIC: str = os.getenv("GCP_PUBSUB_TOPIC", "pqrsd-ingestion-topic")

    # === 📧 NOTIFICACIONES CERTIFICADAS (GCP-SMTPS) ===
    GCP_SMTP_HOST: str = os.getenv("GCP_SMTP_HOST", "smtp.gmail.com")
    GCP_SMTP_PORT: int = int(os.getenv("GCP_SMTP_PORT", 587))
    GCP_SMTP_USER: str = os.getenv("GCP_SMTP_USER", "notificaciones@cali.gov.co")
    GCP_SMTP_PASS: str = os.getenv("GCP_SMTP_PASS", "")
    GCP_EMAIL_SENDER: str = os.getenv("GCP_EMAIL_SENDER", "Alcaldía de Cali <notificaciones@cali.gov.co>")

    # === 🛑 FALLBACKS DE COMPATIBILIDAD (Azure Legacy - No tocar) ===
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_VERSION: Optional[str] = "2024-02-15-preview"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_EMBEDDING_DIMENSIONS: int = 768

    # === 📊 MONITOREO ===
    ENABLE_DETERMINISTIC_MODE: bool = True
    MIN_GROUNDING_RATIO: float = 0.95

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True
    )

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
