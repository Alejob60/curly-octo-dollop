from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.core.auth import create_access_token
from app.core.config import settings
from app.core.auth_realculture import realculture_auth
from loguru import logger
import httpx

router = APIRouter()

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    tenantId: str # UUID según manual

class UserLogin(BaseModel):
    email: EmailStr
    password: str

@router.post("/register", status_code=201)
async def register(user_in: UserRegister):
    """
    AUTH-EXT: Delegación de registro a RealCulture AI Backend.
    """
    return await realculture_auth.register(
        name=user_in.name,
        email=user_in.email,
        password=user_in.password,
        tenant_id=user_in.tenantId
    )

@router.post("/login")
async def login(user_in: UserLogin):
    """
    AUTH-EXT: Delegación de login a RealCulture AI Backend.
    """
    return await realculture_auth.login(
        email=user_in.email,
        password=user_in.password
    )

@router.post("/sync-main-backend-token")
async def sync_main_backend_token(payload: UserLogin):
    """
    Obtiene token desde el backend de RealCulture (antes Main Backend URL).
    """
    return await realculture_auth.login(
        email=payload.email,
        password=payload.password
    )
