from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from loguru import logger

# Base para los modelos SQL (ARCH-1.1)
Base = declarative_base()

class PostgresManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PostgresManager, cls).__new__(cls)
            cls._instance.engine = create_async_engine(
                settings.get_database_url, 
                echo=False,
                pool_pre_ping=True
            )
            cls._instance.session_factory = async_sessionmaker(
                cls._instance.engine, 
                expire_on_commit=False, 
                class_=AsyncSession
            )
        return cls._instance

    def get_session(self) -> AsyncSession:
        return self._instance.session_factory()

class MongoManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoManager, cls).__new__(cls)
            try:
                cls._instance.client = AsyncIOMotorClient(settings.MONGO_URL)
                cls._instance.db = cls._instance.client[settings.MONGO_DB]
                logger.info(f"🍃 [MONGO] Conectado exitosamente a DB: {settings.MONGO_DB}")
            except Exception as e:
                logger.error(f"❌ [MONGO] Error de conexión: {e}")
                cls._instance.client = None
                cls._instance.db = None
        return cls._instance

    def get_db(self):
        return self._instance.db

import redis.asyncio as redis

class ValkeyManager:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ValkeyManager, cls).__new__(cls)
            connection_url = settings.VALKEY_URL or settings.REDIS_URL
            cls._instance.client = redis.from_url(
                connection_url, 
                encoding="utf-8", 
                decode_responses=True,
                socket_timeout=5.0, # Timeout de 5s para no congelar el sistema
                socket_connect_timeout=5.0
            )
        return cls._instance

    async def check_connection(self):
        try:
            await self.client.ping()
            logger.success(f"✅ Conexión a VALKEY establecida exitosamente en {settings.VALKEY_HOST}")
            return True
        except Exception as e:
            logger.error(f"❌ FALLO CRÍTICO DE CONEXIÓN A VALKEY: {e}")
            return False

# Instancias Globales (Singletons)
postgres_manager = PostgresManager()
mongo_manager = MongoManager()
valkey_manager = ValkeyManager()

# Compatibilidad con código existente
AsyncSessionLocal = postgres_manager.session_factory
mongo_db = mongo_manager.get_db()
redis_client = valkey_manager.client
