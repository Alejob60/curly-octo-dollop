from typing import List, Optional

from pydantic import BaseModel, Field


class PqrsTypeItem(BaseModel):
    id: str
    name: str


class DependencyItem(BaseModel):
    id: str
    name: str


class MasterDataResponse(BaseModel):
    pqrs_types: List[PqrsTypeItem]
    dependencies: List[DependencyItem]
    source: str = Field(default="database")


class SmartRoutingRequest(BaseModel):
    topic: str = Field(default="")
    content: str = Field(default="")
    minimum_confidence: float = Field(default=0.85, ge=0.1, le=0.99)


class SmartRoutingResponse(BaseModel):
    suggested_dependency_id: Optional[str] = None
    confidence_score: float
    suggested_dependency_name: Optional[str] = None
    should_autoselect: bool
    reasoning: str
