from fastapi import APIRouter, HTTPException
from app.core.db_clients import mongo_db
from loguru import logger

router = APIRouter()

@router.get("/{task_id}")
async def get_task_status(task_id: str):
    """
    REAL-04: Endpoint de Polling para consultar el estado del procesamiento de Vertex AI.
    """
    try:
        # Consultamos el resultado en la colección task_results de MongoDB
        task_data = await mongo_db.task_results.find_one({"task_id": task_id})
        
        if not task_data:
            return {"status": "PENDING", "message": "Tarea en cola o procesando..."}
            
        # Limpiamos el _id de MongoDB para la respuesta JSON
        task_data.pop("_id", None)
        return task_data

    except Exception as e:
        logger.error(f"Error consultando tarea {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno consultando estado de tarea")
