from sqlalchemy.future import select
from app.core.db_clients import AsyncSessionLocal
from app.models.sql_models import UserProfile
from app.services.cache_service import cache_service
from loguru import logger
import json

class UserProfileService:
    """
    ARCH-1.2: Gestión de Perfiles de Usuario con Cache L2.
    """
    
    async def get_or_create(self, cc: str, defaults: dict = None) -> UserProfile:
        from app.services.crypto_service import crypto_service
        # 1. Intentar desde Cache (L1)
        cache_key = f"user_profile:{cc}"
        cached = await cache_service.get_response(cache_key)
        if cached:
            return cached

        # 2. Consultar PostgreSQL (L2)
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).filter(UserProfile.cc == cc))
            user = result.scalars().first()
            
            if not user and defaults:
                logger.info(f"🆕 Creando nuevo perfil CIFRADO para CC: {cc}")
                user = UserProfile(
                    cc=cc,
                    nombre_completo=crypto_service.encrypt(defaults.get("nombre_completo", "Ciudadano")),
                    direccion_notificacion=crypto_service.encrypt(defaults.get("direccion_notificacion")),
                    emails=[{"valor": defaults.get("email"), "verificado": False}] if defaults.get("email") else []
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            
            if user:
                # Mapear a dict para el cache (DESCIFRADO en el objeto de retorno)
                user_dict = {
                    "cc": user.cc,
                    "nombre_completo": crypto_service.decrypt(user.nombre_completo),
                    "direccion_notificacion": crypto_service.decrypt(user.direccion_notificacion),
                    "emails": user.emails,
                    "telefonos": user.telefonos
                }
                await cache_service.set_response(cache_key, user_dict, ttl=3600*24)
                return user_dict
                
        return None

    async def update_profile(self, cc: str, data: dict):
        from app.services.crypto_service import crypto_service
        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(select(UserProfile).filter(UserProfile.cc == cc))
                user = result.scalars().first()
                if user:
                    for key, val in data.items():
                        if hasattr(user, key):
                            # CIFRAMOS antes de guardar en DB
                            if key in ["nombre_completo", "direccion_notificacion"]:
                                setattr(user, key, crypto_service.encrypt(val))
                            else:
                                setattr(user, key, val)
                    await session.commit()
                    # Invalidar Cache
                    await cache_service.redis_client.delete(f"ai_cache:{cache_service._generate_key(f'user_profile:{cc}')}")
                    logger.info(f"✅ Perfil CC {cc} actualizado con CIFRADO.")

user_profile_service = UserProfileService()
