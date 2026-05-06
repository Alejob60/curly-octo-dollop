from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.auth import get_current_user
from app.schemas.judicial import JudicialParseResponse
from app.services.judicial_parser_service import judicial_parser_service

router = APIRouter()


@router.post("/parse-demand", response_model=JudicialParseResponse)
async def parse_judicial_demand(
    file: UploadFile = File(...),
    case_type: str = "JUDICIAL_DEMAND",
    _user=Depends(get_current_user),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

    try:
        file_bytes = await file.read()
        result = await judicial_parser_service.parse_demand_pdf(file_bytes, case_type=case_type)
        return JudicialParseResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error procesando demanda judicial: {exc}")
