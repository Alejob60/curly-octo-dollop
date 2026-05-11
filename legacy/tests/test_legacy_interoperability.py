import pytest
import httpx
from app.integrations.legacy_bridge import orfeo_bridge, saul_bridge, sap_bridge
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_orfeo_batch_extraction():
    """Valida la extracción cursor-based de Orfeo."""
    mock_response = {
        "data": [{"radicado": "2026-ABC-01", "asunto": "Test"}],
        "next_cursor": "ABC-02"
    }
    
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value.json.return_value = mock_response
        mock_req.return_value.status_code = 200
        
        result = await orfeo_bridge.get_pqrs_batch(limit=1)
        
        assert result["next_cursor"] == "ABC-02"
        assert len(result["data"]) == 1

@pytest.mark.asyncio
async def test_saul_predio_lookup():
    """Valida la consulta de predios en SAUL."""
    mock_response = {"matricula": "123-456", "direccion": "Av 6ta"}
    
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value.json.return_value = mock_response
        mock_req.return_value.status_code = 200
        
        result = await saul_bridge.get_predio("123-456")
        assert result["matricula"] == "123-456"

@pytest.mark.asyncio
async def test_circuit_breaker_activation():
    """Valida que el circuit breaker bloquee tras fallos continuos."""
    from app.integrations.legacy_bridge import OrfeoBridge
    test_bridge = OrfeoBridge()
    
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = Exception("API Down")
        
        # Simulamos 10 fallos
        for _ in range(11):
            await test_bridge.get_pqrs_batch()
            
        # El siguiente debería fallar por CB sin llamar a httpx
        mock_req.reset_mock()
        result = await test_bridge.get_pqrs_batch()
        
        assert result is None
        mock_req.assert_not_called()
