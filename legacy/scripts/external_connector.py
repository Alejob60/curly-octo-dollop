import asyncio
import httpx
from loguru import logger
from app.core.config import settings

async def pull_from_external_source(source_name: str, api_url: str):
    """
    Simula un conector que extrae datos de un sistema externo (SAP u Orfeo)
    y los envía al Gateway de Orbital Prime.
    """
    logger.info(f"Iniciando extracción desde {source_name}...")
    
    # Simulación de datos crudos "sucios" de un sistema legado
    legacy_data = {
        "radicado_nro": "ORF-2026-0001",
        "remitente": "Juan Perez",
        "identificacion": "1.110.222.333",
        "email": "juan.perez@email.com",
        "texto_solicitud": "Solicito información sobre el catastro de mi vivienda.",
        "tipo": "Derecho de Petición"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"http://localhost:8000/api/v1/ingesta/?source_type=ORFEO",
                json=legacy_data,
                headers={"X-API-KEY": settings.INTERNAL_API_KEY}
            )
            
            if response.status_code == 200:
                logger.success(f"Dato de {source_name} procesado por el Bridge: {response.json()}")
            else:
                logger.error(f"Error en el Bridge: {response.text}")
                
        except Exception as e:
            logger.error(f"Error de conexión con el Gateway: {str(e)}")

if __name__ == "__main__":
    # Para probar esto el servidor uvicorn debe estar corriendo
    asyncio.run(pull_from_external_source("ORFEO_DISTRITO", "http://localhost:8000"))
