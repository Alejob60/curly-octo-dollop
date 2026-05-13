import asyncio
from datetime import datetime
from app.core.db_clients import postgres_manager
from app.models.sql_models import IntegrationConnector
from app.integrations.base_adapter import RESTAdapter, DBAdapter
from sqlalchemy import select
from loguru import logger

class SyncEngine:
    """
    Motor de Sincronización Universal V1.0.
    Orquesta la extracción y empuje de datos entre Orbital y Legacy Systems.
    """
    ADAPTERS = {
        "rest": RESTAdapter(),
        "database": DBAdapter()
    }

    async def sync_connector(self, connector_id: str):
        async with postgres_manager.get_session() as session:
            result = await session.execute(select(IntegrationConnector).where(IntegrationConnector.id == connector_id))
            connector = result.scalar_one_or_none()
            
            if not connector or connector.status != "active":
                logger.warning(f"⚠️ Conector {connector_id} no disponible para sync.")
                return

            adapter = self.ADAPTERS.get(connector.protocol)
            if not adapter:
                logger.error(f"❌ Protocolo {connector.protocol} no soportado.")
                return

            try:
                # 1. Test de Salud
                if not await adapter.test_connection(connector.config):
                    connector.health_status = "unhealthy"
                    await session.commit()
                    return

                # 2. Extracción Incremental
                # (Lógica simplificada para el Sprint 1)
                logger.info(f"🔄 Sincronizando {connector.name}...")
                
                connector.last_sync_at = datetime.utcnow()
                connector.health_status = "healthy"
                connector.last_sync_status = "SUCCESS"
                await session.commit()
                
            except Exception as e:
                logger.error(f"❌ Fallo en sync de {connector.name}: {e}")
                connector.last_sync_status = "ERROR"
                connector.last_error = str(e)
                connector.health_status = "unhealthy"
                await session.commit()

sync_engine = SyncEngine()
