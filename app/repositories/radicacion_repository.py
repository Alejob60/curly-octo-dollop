from app.repositories.base import SQLRepository, MongoRepository
from app.core.db_clients import postgres_manager, mongo_manager
from loguru import logger

class RadicacionRepository:
    """
    UoW (Unit of Work) simplificado para Radicaciones Híbridas.
    Maneja SQL para la estructura y Mongo para el contenido denso.
    """
    def __init__(self):
        self.mongo = MongoRepository("final_records", mongo_manager.get_db())

    async def save_full_radicado(self, sql_data: dict, mongo_data: dict):
        # 1. Persistencia Documental (Mongo) - Siempre guardamos el rastro completo
        mongo_id = await self.mongo.insert(mongo_data)
        
        # 2. Persistencia Estructural (Postgres)
        # Aquí se inyectaría la lógica de SQLAlchemy si fuera necesario
        # Por ahora mantenemos la compatibilidad con el flujo de citizen_submit
        logger.info(f"Radicado persistido en Mongo: {mongo_id}")
        return mongo_id

radicado_repo = RadicacionRepository()
