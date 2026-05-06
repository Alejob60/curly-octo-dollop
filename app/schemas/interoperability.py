from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class IntegrationKeyCreateRequest(BaseModel):
    system_name: str = Field(..., min_length=2, max_length=120)
    dependency_code: str = Field(..., min_length=2, max_length=40)
    permissions: list[str] = Field(default_factory=lambda: ["write"])
    allowed_ips: list[str] = Field(default_factory=list)
    expires_in_days: int = Field(default=30, ge=1, le=365)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntegrationKeyResponse(BaseModel):
    key_id: str
    api_key: str
    system_name: str
    dependency_code: str
    permissions: list[str]
    allowed_ips: list[str]
    expires_at: datetime
    created_at: datetime


class IntegrationKeySummary(BaseModel):
    key_id: str
    system_name: str
    dependency_code: str
    permissions: list[str]
    allowed_ips: list[str]
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_by: Optional[str] = None


class IntegrationKeyRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=240)


class InteroperabilityLogEntry(BaseModel):
    event_type: str
    key_id: Optional[str] = None
    system_name: Optional[str] = None
    dependency_code: Optional[str] = None
    source_ip: Optional[str] = None
    status: str
    detail: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class MobilityRealtimeEvent(BaseModel):
    intersection_id: str
    signal_status: str
    congestion_level: float = Field(..., ge=0, le=1)
    average_speed_kmh: Optional[float] = None
    incident_code: Optional[str] = None
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)