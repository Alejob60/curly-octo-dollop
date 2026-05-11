# import pytest
import asyncio
import uuid
import os
import sys

# Asegurar que se encuentre el módulo app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.privacy_shield_service import privacy_shield
from app.models.sql_models import SessionToken
from app.core.db_clients import postgres_manager
from sqlalchemy import select

async def test_pii_tokenization_mechanics():
    """
    Certificación de enmascaramiento de datos sensibles.
    """
    session_id = f"test-shield-{uuid.uuid4().hex[:6]}"
    original_text = "Solicitud de Juan Perez CC 10300452 con correo jp@gmail.com y tel 3172272984."
    
    # 1. Ejecutar Tokenización
    tokenized = await privacy_shield.tokenize_text(session_id, original_text)
    
    # Validaciones
    assert "10300452" not in tokenized
    assert "jp@gmail.com" not in tokenized
    assert "3172272984" not in tokenized
    assert "[ID_1]" in tokenized or "[ID_2]" in tokenized # Regex matches multiple
    
    # 2. Verificar persistencia en Postgres
    async with postgres_manager.get_session() as session:
        stmt = select(SessionToken).where(SessionToken.session_id == session_id)
        res = await session.execute(stmt)
        tokens = res.scalars().all()
        assert len(tokens) >= 3 # ID, EMAIL, PHONE
        
    # 3. Rehidratación
    rehydrated = await privacy_shield.rehydrate_text(session_id, tokenized)
    assert "10300452" in rehydrated
    assert "jp@gmail.com" in rehydrated
    
    # 4. Limpieza
    await privacy_shield.cleanup_session(session_id)
    async with postgres_manager.get_session() as session:
        stmt = select(SessionToken).where(SessionToken.session_id == session_id)
        res = await session.execute(stmt)
        assert len(res.scalars().all()) == 0

if __name__ == "__main__":
    # Permite ejecutarlo como script individual
    asyncio.run(test_pii_tokenization_mechanics())
    print("✅ test_privacy_shield_unit: PASSED")
