import jwt
from datetime import datetime, timedelta
from typing import Optional, Union
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from loguru import logger
import httpx

# Configuración de hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 día


async def _validate_token_with_main_backend(token: str) -> Optional[dict]:
    """Fallback validation when token was issued by the external Misybot backend."""
    try:
        verify_url = f"{settings.MAIN_BACKEND_URL.rstrip('/')}{settings.MAIN_BACKEND_VERIFY_PATH}"
        async with httpx.AsyncClient(timeout=settings.MAIN_BACKEND_TIMEOUT_SECONDS) as client:
            response = await client.get(
                verify_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code >= 400:
                return None

            data = response.json() if response.content else {}
            tenant_id = (
                data.get("tenant_id")
                or data.get("tenantId")
                or (data.get("user") or {}).get("tenant_id")
                or (data.get("user") or {}).get("tenantId")
            )
            user_id = (
                data.get("user_id")
                or data.get("sub")
                or (data.get("user") or {}).get("id")
                or (data.get("user") or {}).get("user_id")
            )
            email = data.get("email") or (data.get("user") or {}).get("email")

            return {
                "user_id": str(user_id) if user_id else None,
                "email": email,
                "tenant_id": tenant_id,
            }
    except Exception as exc:
        logger.warning(f"No fue posible validar token con MAIN_BACKEND_URL: {exc}")
        return None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_api_key(
    x_api_key: str = Header(...),
    request: Request = None
):
    """
    Validador de API Key para sistemas integrados (The Orbital Bridge).
    """
    if x_api_key != settings.INTERNAL_API_KEY:
        logger.warning(f"Intento de acceso con API Key inválida desde: {request.client.host if request else 'Unknown'}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida o ausente"
        )
    return {
        "source_ip": request.client.host if request else "Unknown",
        "key_record": {"key_id": "BUS-DATA-PRO", "system_name": "INSTITUTIONAL_BRIDGE"}
    }

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    x_tenant_id: str = Header(...)
):
    """
    Middleware de validación de JWT y Tenant.
    Asegura que el usuario esté autenticado y pertenezca al tenant correcto.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Validar tenant_id (Multi-tenancy)
        token_tenant = payload.get("tenant_id")
        if token_tenant and token_tenant != x_tenant_id:
            raise HTTPException(status_code=403, detail="Acceso denegado a este Tenant")
            
        return {"user_id": user_id, "email": payload.get("email"), "tenant_id": x_tenant_id}
    except jwt.PyJWTError:
        external_user = await _validate_token_with_main_backend(token)
        if not external_user:
            raise credentials_exception

        external_tenant = external_user.get("tenant_id")
        if external_tenant and external_tenant != x_tenant_id:
            raise HTTPException(status_code=403, detail="Acceso denegado a este Tenant")

        return {
            "user_id": external_user.get("user_id"),
            "email": external_user.get("email"),
            "tenant_id": x_tenant_id,
        }
