from fastapi import APIRouter

from app.schemas.master_data import MasterDataResponse, SmartRoutingRequest, SmartRoutingResponse
from app.services.master_data_service import master_data_service

router = APIRouter()


@router.get("", response_model=MasterDataResponse)
async def get_master_data():
    pqrs_types, dependencies, source = await master_data_service.get_master_data()
    return MasterDataResponse(pqrs_types=pqrs_types, dependencies=dependencies, source=source)


@router.post("/suggest-dependency", response_model=SmartRoutingResponse)
async def suggest_dependency(payload: SmartRoutingRequest):
    result = await master_data_service.suggest_dependency(
        topic=payload.topic,
        content=payload.content,
        minimum_confidence=payload.minimum_confidence,
    )
    return SmartRoutingResponse(**result)
