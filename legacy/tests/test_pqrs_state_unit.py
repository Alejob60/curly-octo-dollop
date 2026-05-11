# import pytest
import asyncio
import uuid
import os
import sys

# Asegurar que se encuentre el módulo app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.pqrs_manager import pqrs_manager
async def test_ui_decision_logic():
    """
    Certificación del motor de decisiones de Cards (Épica 3).
    """
    session_id = "test-logic-123"

    # Caso 1: Todo Nulo -> Debe pedir Identidad o avanzar si hay perfil
    data_empty = pqrs_manager._get_empty_schema()
    res1 = await pqrs_manager.get_next_ui_instruction(session_id, data=data_empty)
    # Aceptamos IdentityCard o SuccessCard (si hay bypass)
    assert res1["type"] in ["card", "command"]

    # Caso 2: Identidad llena (documento, nombres, primer_apellido), falta contacto
    data_id_full = {
        **data_empty, 
        "documento": "10300452", 
        "nombres": "Alejandro", 
        "primer_apellido": "Garzon"
    }
    res2 = await pqrs_manager.get_next_ui_instruction(session_id, data=data_id_full)
    assert res2["cardType"] == "ContactCard"

    
    # Caso 3: Identidad y Contacto llenos -> Debe pedir EvidenceAndLegalCard
    data_contact_full = {**data_id_full, "email": "a@g.com", "celular": "3172272984", "direccion": "Calle 5"}
    res3 = await pqrs_manager.get_next_ui_instruction(session_id, data_contact_full)
    assert res3["cardType"] == "EvidenceAndLegalCard"
    
    # Caso 4: Todo lleno -> Ready for Signature
    data_all_full = {**data_contact_full, "autorizacion_datos": True}
    res4 = await pqrs_manager.get_next_ui_instruction(session_id, data_all_full)
    assert res4["command"] == "READY_FOR_SIGNATURE"

if __name__ == "__main__":
    asyncio.run(test_ui_decision_logic())
    print("✅ test_pqrs_state_unit: PASSED")
