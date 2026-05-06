import re
import uuid
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.sql_models import SessionToken
from app.core.db_clients import postgres_manager
from loguru import logger

class PrivacyShieldService:
    """
    V48.1: Motor de Anonimización Forense Orbital.
    Protege el Habeas Data bloqueando el acceso de la IA a PII real.
    Mejorado para detección de nombres propios por patrones.
    """

    def __init__(self):
        # Patrones mejorados para el contexto colombiano
        self.patterns = {
            "ID": r"\b\d{7,15}\b", # Cédulas/NIT
            "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "PHONE": r"\b3\d{9}\b", # Celulares
            # Detección de Nombres (Patrón: "Nombre es X" o "Mi nombre es X")
            # Mejorado: permite 'y', 'con', o simplemente espacios al final
            "NAME_HINT": r"(?:nombre es|peticionario:|soy)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ\s]{3,40})(?=\s*[\.,]|\s+y\s+|\s+con\s+|\s*$)"
        }

    async def tokenize_text(self, session_id: str, text: str) -> str:
        """
        Captura PII, la cifra con AES-256 y la guarda en PostgreSQL reemplazando por tokens.
        """
        from app.services.crypto_service import crypto_service
        async with postgres_manager.get_session() as session:
            tokenized_text = text
            
            # 1. Primero detectar nombres por pista lingüística
            name_match = re.search(self.patterns["NAME_HINT"], text, re.IGNORECASE)
            if name_match:
                real_name = name_match.group(1).strip()
                token_key = "[NOMBRE_1]"
                new_token = SessionToken(
                    session_id=session_id,
                    token_key=token_key,
                    token_value=crypto_service.encrypt(real_name), # CIFRADO
                    expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=72)
                )
                session.add(new_token)
                tokenized_text = tokenized_text.replace(real_name, token_key)

            # 2. Detectar otros patrones técnicos
            for pii_type, pattern in self.patterns.items():
                if pii_type == "NAME_HINT": continue 
                
                matches = re.findall(pattern, tokenized_text)
                for i, match in enumerate(set(matches)):
                    token_key = f"[{pii_type}_{i+1}]"
                    
                    new_token = SessionToken(
                        session_id=session_id,
                        token_key=token_key,
                        token_value=crypto_service.encrypt(match), # CIFRADO
                        expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=72)
                    )
                    session.add(new_token)
                    tokenized_text = tokenized_text.replace(match, token_key)
            
            await session.commit()
            logger.info(f"🛡️ Escudo V50.2: Texto anonimizado y CIFRADO para {session_id}.")
            return tokenized_text

    async def get_full_pii_mapping(self, session_id: str) -> dict:
        """Obtiene todo el mapping de tokens -> valores reales (descifrados) para una sesión."""
        from app.services.crypto_service import crypto_service
        async with postgres_manager.get_session() as session:
            stmt = select(SessionToken).where(SessionToken.session_id == session_id)
            result = await session.execute(stmt)
            tokens = result.scalars().all()
            mapping = {t.token_key: crypto_service.decrypt(t.token_value) for t in tokens}
            logger.debug(f"🔑 [SHIELD_MAP] Recuperados {len(mapping)} tokens para rehidratación.")
            return mapping

    async def rehydrate_text(self, session_id: str, anonymized_text: str) -> str:
        if not anonymized_text:
            return anonymized_text

        mapping = await self.get_full_pii_mapping(session_id)
        rehydrated_text = str(anonymized_text)
        
        for token, real_val in mapping.items():
            # Intentamos con corchetes (estándar)
            if token in rehydrated_text:
                rehydrated_text = rehydrated_text.replace(token, real_val)
            
            # Intentamos sin corchetes por si la IA los omitió (limpieza agresiva)
            token_raw = token.replace("[", "").replace("]", "")
            if token_raw in rehydrated_text:
                # Usamos regex para asegurar que sea el token exacto y no parte de otra palabra
                pattern = r'\b' + re.escape(token_raw) + r'\b'
                rehydrated_text = re.sub(pattern, real_val, rehydrated_text)
        
        return rehydrated_text

    async def deep_rehydrate(self, session_id: str, data: any) -> any:
        """
        Rehidrata recursivamente cualquier estructura de datos (dict, list, str).
        Garantiza que ningún token quede sin procesar en el dossier final.
        """
        mapping = await self.get_full_pii_mapping(session_id)
        
        def _rehydrate_recursive(item):
            if isinstance(item, str):
                if "[" not in item: return item
                # Optimizamos: solo iterar si detectamos posible token
                res = item
                for token, real_val in mapping.items():
                    if token in res:
                        res = res.replace(token, real_val)
                return res
            elif isinstance(item, list):
                return [_rehydrate_recursive(i) for i in item]
            elif isinstance(item, dict):
                return {k: _rehydrate_recursive(v) for k, v in item.items()}
            return item

        return _rehydrate_recursive(data)

    async def cleanup_session(self, session_id: str):
        async with postgres_manager.get_session() as session:
            stmt = delete(SessionToken).where(SessionToken.session_id == session_id)
            await session.execute(stmt)
            await session.commit()
            logger.info(f"🧹 Tokens eliminados para sesión {session_id}.")

privacy_shield = PrivacyShieldService()
