from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx
import asyncpg
import json
from loguru import logger

class BaseAdapter(ABC):
    @abstractmethod
    async def test_connection(self, config: Dict[str, Any]) -> bool: pass
    
    @abstractmethod
    async def fetch_data(self, config: Dict[str, Any], mapping: Dict[str, Any], 
                         last_sync_value: Optional[str] = None) -> List[Dict]: pass
    
    @abstractmethod
    async def push_data(self, config: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]: pass

class RESTAdapter(BaseAdapter):
    async def test_connection(self, config: Dict[str, Any]) -> bool:
        try:
            async with httpx.AsyncClient(timeout=config.get("timeout", 10)) as client:
                res = await client.get(config["base_url"])
                return res.status_code < 500
        except Exception as e:
            logger.error(f"❌ REST Connection failed: {e}")
            return False

    async def fetch_data(self, config, mapping, last_sync_value=None):
        async with httpx.AsyncClient(base_url=config["base_url"]) as client:
            res = await client.get(config["endpoint"])
            res.raise_for_status()
            data = res.json()
            return [self._apply_mapping(r, mapping) for r in (data if isinstance(data, list) else [data])]

    async def push_data(self, config, payload):
        async with httpx.AsyncClient(base_url=config["base_url"]) as client:
            res = await client.post(config["endpoint"], json=payload)
            res.raise_for_status()
            return res.json()

    def _apply_mapping(self, record: Dict, mapping: Dict) -> Dict:
        return {orbital: record.get(legacy) for legacy, orbital in mapping.items()}

class DBAdapter(BaseAdapter):
    async def test_connection(self, config: Dict[str, Any]) -> bool:
        try:
            conn = await asyncpg.connect(dsn=config["dsn"])
            await conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ DB Connection failed: {e}")
            return False

    async def fetch_data(self, config, mapping, last_sync_value=None):
        conn = await asyncpg.connect(dsn=config["dsn"])
        rows = await conn.fetch(config["query"])
        await conn.close()
        return [{orbital: row[legacy] for legacy, orbital in mapping.items()} for row in rows]

    async def push_data(self, config, payload):
        # Implementación de insert/update legacy si es necesario
        return {"status": "success"}
