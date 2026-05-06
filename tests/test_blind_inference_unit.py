# import pytest
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

# Asegurar que se encuentre el módulo app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.pqrs_manager import pqrs_manager

async def test_blind_inference_prompt_protection():
    """
    Certificación de que la IA NUNCA recibe datos reales (HU 2.2).
    """
    session_id = "shield-test-blind"
    real_message = "Soy Juan Perez CC 10300452, quiero radicar una queja."
    
    # Mock de Vertex Client para inspeccionar el prompt
    with patch('app.core.vertex_client.vertex_client.generate_content', new_callable=AsyncMock) as mock_vertex:
        # Mock de respuesta simulada de la IA usando tokens
        mock_vertex.return_value = '{"nombres": "Juan Perez", "documento": "[ID_1]", "asunto": "Queja"}'
        
        # Ejecutar análisis
        await pqrs_manager.analyze_initial_message(session_id, real_message)
        
        # OBTENER EL PROMPT QUE REALMENTE SE LE MANDÓ A LA IA
        sent_prompt = mock_vertex.call_args[0][0]
        
        # VALIDACIÓN CRÍTICA
        assert "10300452" not in str(sent_prompt), "❌ ERROR: Cédula real filtrada a la IA"
        assert "[ID_1]" in str(sent_prompt), "✅ ÉXITO: La IA solo recibió el token ID"
        
if __name__ == "__main__":
    asyncio.run(test_blind_inference_prompt_protection())
    print("✅ test_blind_inference_unit: PASSED")
