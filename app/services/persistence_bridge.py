from sqlalchemy import select, update
from app.core.db_clients import postgres_manager
from app.models.sql_models import CaseRegistry
import datetime
import json
from typing import Dict, Any, Optional
from loguru import logger

class PersistenceBridge:
    """
    SPRINT 1: Puente de Persistencia Progresiva.
    Garantiza que el progreso se guarde en PostgreSQL en cada hito crítico.
    """
    async def save_progress(self, session_id: str, radicado: str, phase_data: Dict[str, Any]):
        """
        SPRINT 1.1: Upsert Atómico Resiliente.
        Evita errores de duplicidad buscando por Radicado o SessionID.
        """
        async with postgres_manager.get_session() as session:
            try:
                # 1. Búsqueda exhaustiva - Priorizamos Radicado, luego SessionID (Tomamos el más reciente)
                from sqlalchemy import desc
                stmt = select(CaseRegistry).where(
                    (CaseRegistry.radicado == radicado) | 
                    (CaseRegistry.session_id == session_id)
                ).order_by(desc(CaseRegistry.created_at))
                
                result = await session.execute(stmt)
                record = result.scalars().first() # Tomamos el más reciente si hay colisión
                
                if not record:
                    record = CaseRegistry(
                        session_id=session_id, 
                        radicado=radicado,
                        estado="EN_PROCESO",
                        created_at=datetime.datetime.utcnow()
                    )
                    session.add(record)
                    logger.info(f"🆕 [BRIDGE] Creando registro nuevo: {radicado}")
                else:
                    logger.info(f"🔄 [BRIDGE] Actualizando registro existente: {radicado}")
                
                # 2. Sincronización de campos con limpieza de nulos
                for key, value in phase_data.items():
                    if hasattr(record, key) and value is not None:
                        # Manejo especial para listas/JSON (Deduplicación segura V55.9)
                        if key in ["completed_phases", "citas_verificables"] and isinstance(value, list):
                            current = getattr(record, key) or []
                            # Unificamos listas evitando el error de 'unhashable type: dict'
                            combined = current + value
                            unique_list = []
                            seen = set()
                            for item in combined:
                                # Creamos una representación estable para detectar duplicados
                                item_repr = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
                                if item_repr not in seen:
                                    unique_list.append(item)
                                    seen.add(item_repr)
                            setattr(record, key, unique_list)
                        else:
                            setattr(record, key, value)
                
                record.updated_at = datetime.datetime.utcnow()
                await session.commit()
                logger.success(f"💾 [BRIDGE] Sincronización exitosa para {radicado}")
                
            except Exception as e:
                logger.error(f"❌ [BRIDGE] Error crítico en UPSERT: {e}")
                await session.rollback()
                raise

    async def load_case(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Carga el estado completo desde la Bóveda de PostgreSQL."""
        async with postgres_manager.get_session() as session:
            stmt = select(CaseRegistry).where(CaseRegistry.session_id == session_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if not record: return None
            
            return {c.name: getattr(record, c.name) for c in record.__table__.columns}

persistence_bridge = PersistenceBridge()
