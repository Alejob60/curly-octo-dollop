from sqlalchemy import select, update
from app.core.db_clients import postgres_manager
from app.models.sql_models import CaseRegistry
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

class CasePersistence:
    """
    V56.3: Servicio de Persistencia Evolutiva para Expedientes PQRSD.
    Gestiona el ciclo de vida del dato en PostgreSQL para auditoría y dashboard.
    """

    async def save_progress(self, radicado: str, session_id: str, phase_data: Dict[str, Any]):
        """
        Guarda o actualiza el progreso de un caso en PostgreSQL.
        Funciona de forma acumulativa (Merge).
        """
        async with postgres_manager.get_session() as session:
            try:
                # 1. Buscar registro existente
                stmt = select(CaseRegistry).where(CaseRegistry.radicado == radicado)
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                
                if not record:
                    # Crear nuevo registro base
                    record = CaseRegistry(
                        radicado=radicado, 
                        session_id=session_id,
                        estado="INICIADO",
                        created_at=datetime.utcnow()
                    )
                    session.add(record)
                    logger.info(f"🆕 [PERSISTENCE] Creando nuevo registro para radicado {radicado}")
                
                # 2. Actualizar campos dinámicamente si el record tiene el atributo
                for key, value in phase_data.items():
                    if hasattr(record, key):
                        # Manejo especial para listas acumulativas
                        if key == "completed_phases" and isinstance(value, list):
                            current_phases = record.completed_phases or []
                            record.completed_phases = list(set(current_phases + value))
                        else:
                            setattr(record, key, value)
                
                record.updated_at = datetime.utcnow()
                await session.commit()
                logger.success(f"💾 [PERSISTENCE] Progreso guardado para {radicado}")
                
            except Exception as e:
                logger.error(f"❌ [PERSISTENCE] Fallo al guardar progreso para {radicado}: {e}")
                await session.rollback()

    async def load_case(self, radicado: str) -> Optional[Dict[str, Any]]:
        """Carga un caso completo desde PostgreSQL para el dashboard o copiloto."""
        async with postgres_manager.get_session() as session:
            stmt = select(CaseRegistry).where(CaseRegistry.radicado == radicado)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            
            if not record:
                return None
            
            # Convertir a diccionario plano
            return {c.name: getattr(record, c.name) for c in record.__table__.columns}

    async def mark_as_finalized(self, radicado: str, user_id: str, pdf_hashes: Dict[str, str], pdf_paths: Dict[str, str]):
        """Marca un caso como finalizado tras el firmado KMS."""
        async with postgres_manager.get_session() as session:
            try:
                stmt = update(CaseRegistry).where(CaseRegistry.radicado == radicado).values(
                    estado="FIRMADO",
                    signed_at=datetime.utcnow(),
                    signed_by=user_id,
                    pdf_hashes=pdf_hashes,
                    pdf_paths=pdf_paths,
                    updated_at=datetime.utcnow()
                )
                await session.execute(stmt)
                await session.commit()
                logger.success(f"⚖️ [PERSISTENCE] Caso {radicado} marcado como FINALIZADO/FIRMADO")
            except Exception as e:
                logger.error(f"❌ [PERSISTENCE] Fallo al finalizar caso {radicado}: {e}")

case_persistence = CasePersistence()
