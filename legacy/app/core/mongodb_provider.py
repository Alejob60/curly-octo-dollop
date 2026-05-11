"""
MongoDB Provider Adapter - Supports both Azure Cosmos DB and Google Cloud MongoDB Atlas.
Maintains identical interface for seamless provider switching.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class MongoDBProviderFactory:
    """Factory for creating MongoDB clients that support multiple providers."""
    
    _instance: Optional[AsyncIOMotorDatabase] = None
    _client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """
        Get or create MongoDB client based on provider configuration.
        Supports:
        - "cosmos": Azure Cosmos DB (MongoDB-compatible API)
        - "atlas": MongoDB Atlas (on GCP infrastructure)
        - "local": Local MongoDB instance
        """
        if cls._client is not None:
            return cls._client
        
        provider = settings.MONGODB_PROVIDER.lower()
        mongo_url = settings.MONGO_URL
        
        logger.info(f"Initializing MongoDB provider: {provider}")
        
        if provider == "cosmos":
            # Azure Cosmos DB MongoDB compatible endpoint
            logger.info("Connecting to Azure Cosmos DB (MongoDB mode)")
            cls._client = AsyncIOMotorClient(
                mongo_url,
                tls=True,
                authMechanism="SCRAM-SHA-256",
                retryWrites=False,
                maxIdleTimeMS=120000,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
            )
        elif provider == "atlas":
            # MongoDB Atlas (can run on GCP)
            logger.info("Connecting to MongoDB Atlas on GCP")
            cls._client = AsyncIOMotorClient(
                mongo_url,
                tls=True,
                authMechanism="SCRAM-SHA-256",
                # Atlas supports retries unlike Cosmos
                retryWrites=True,
                maxPoolSize=50,
                minPoolSize=10,
            )
        elif provider == "local":
            # Local MongoDB for development
            logger.info("Connecting to local MongoDB instance")
            cls._client = AsyncIOMotorClient(
                mongo_url or "mongodb://localhost:27017",
                serverSelectionTimeoutMS=5000,
            )
        else:
            raise ValueError(f"Unknown MongoDB provider: {provider}")
        
        return cls._client
    
    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        """Get or create MongoDB database connection."""
        if cls._instance is not None:
            return cls._instance
        
        client = cls.get_client()
        db_name = settings.MONGO_DB
        cls._instance = client[db_name]
        
        logger.info(f"Connected to database: {db_name}")
        return cls._instance
    
    @classmethod
    async def close(cls) -> None:
        """Close MongoDB connection."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._instance = None
            logger.info("MongoDB connection closed")
    
    @classmethod
    async def health_check(cls) -> bool:
        """
        Perform health check on MongoDB connection.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            db = cls.get_database()
            # Attempt a simple ping command
            await db.command("ping")
            logger.debug("MongoDB health check passed")
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {str(e)}")
            return False


# Singleton instances
_mongo_client: Optional[AsyncIOMotorClient] = None
_mongo_db: Optional[AsyncIOMotorDatabase] = None


async def get_mongo_client() -> AsyncIOMotorClient:
    """Get MongoDB client instance."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoDBProviderFactory.get_client()
    return _mongo_client


async def get_mongo_database() -> AsyncIOMotorDatabase:
    """Get MongoDB database instance."""
    global _mongo_db
    if _mongo_db is None:
        _mongo_db = MongoDBProviderFactory.get_database()
    return _mongo_db


async def close_mongo_connection() -> None:
    """Close MongoDB connection gracefully."""
    global _mongo_client, _mongo_db
    _mongo_client = None
    _mongo_db = None
    await MongoDBProviderFactory.close()
