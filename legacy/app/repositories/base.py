from typing import Generic, TypeVar, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from motor.motor_asyncio import AsyncIOMotorDatabase

T = TypeVar("T")

class SQLRepository(Generic[T]):
    def __init__(self, model: T, session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: Any) -> Optional[T]:
        result = await self.session.execute(select(self.model).filter_by(id=id))
        return result.scalars().first()

    async def create(self, obj: T) -> T:
        self.session.add(obj)
        await self.session.flush()
        return obj

class MongoRepository:
    def __init__(self, collection_name: str, db: AsyncIOMotorDatabase):
        self.collection = db[collection_name]

    async def insert(self, document: dict) -> str:
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def find_one(self, filter: dict) -> Optional[dict]:
        return await self.collection.find_one(filter)
