import hashlib
import json
import uuid
import datetime
from sqlalchemy import text
from app.core.db_clients import AsyncSessionLocal
from loguru import logger
from app.core.config import settings
from app.services.gcp_storage_service import immutable_storage_service
from app.services.signer import signer_service
import os

class LedgerService:
    def __init__(self):
        # MIGRACIÓN V26.4: Azure -> GCP (WORM + KMS)
        self.provider = settings.LEDGER_PROVIDER
        self._default_tenant_id = None
        self.client = None # Mantener por compatibilidad con gobernanza
        
        logger.info(f"🏛️ Ledger Service inicializado. Proveedor: {self.provider.upper()}")

    @staticmethod
    def calculate_hash(data: dict, previous_hash: str = "") -> str:
        """Calcula el hash SHA-256 de un bloque de datos para el encadenamiento local."""
        block_string = json.dumps(data, sort_keys=True) + previous_hash
        return hashlib.sha256(block_string.encode()).hexdigest()

    async def _get_audit_ledger_columns(self, session) -> set[str]:
        result = await session.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'audit_ledger'")
        )
        return {row[0] for row in result.fetchall()}

    async def _get_default_tenant_id(self, session) -> str | None:
        if self._default_tenant_id:
            return self._default_tenant_id

        try:
            result = await session.execute(text("SELECT id FROM tenants ORDER BY name LIMIT 1"))
            row = result.fetchone()
            if row and row[0]:
                self._default_tenant_id = str(row[0])
                return self._default_tenant_id
        except Exception as exc:
            logger.warning(f"No fue posible resolver tenant por defecto para audit_ledger: {exc}")
        return None

    async def log_event(self, registry_id: str, action: str, payload: dict):
        """
        MIGRACIÓN V26.4: Registra un evento inmutable en GCP (Garantía Legal)
        y luego en Postgres (Auditoría Local).
        """
        try:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            # Preparar datos base
            event_entry = {
                "registry_id": registry_id,
                "action": action,
                "payload": payload,
                "timestamp": timestamp,
                "protocol_version": "V26.4_GCP_LEDGER"
            }
            
            transaction_id = "LOCAL_ONLY"
            gcp_object_path = None
            
            # --- CAPA 1: GCP IMMUTABLE LEDGER (WORM + KMS) ---
            if self.provider == "gcp":
                try:
                    # 1. Generar digest del evento
                    event_digest = self.calculate_hash(event_entry)
                    
                    # 2. Firmar digest con GCP KMS (Soberanía de Datos)
                    signature = signer_service.sign_digest_sha256(event_digest)
                    
                    # 3. Subir a Bucket con Bloqueo de Retención (WORM)
                    gcp_object_path = immutable_storage_service.upload_to_immutable_bucket(
                        payload=event_entry,
                        external_id=registry_id,
                        action=action,
                        signature=signature.get("signature_b64"),
                        digest_sha256=event_digest,
                    )

                    signature_ref = signature.get("key_version") or "NO_KMS"
                    transaction_id = f"GCP::{signature_ref.split('/')[-1]}::{event_digest[:16].upper()}"
                    
                    logger.success(f"🔐 Registro Inmutable GCP: {transaction_id}")
                except Exception as gcp_err:
                    logger.error(f"❌ Fallo crítico en GCP Ledger: {gcp_err}")
            
            # --- CAPA 2: AZURE LEDGER (FALLBACK/DEPRECATED) ---
            elif self.provider == "azure":
                logger.warning("⚠️ Azure Ledger está marcado como DEPRECATED. Migrando a GCP.")
                transaction_id = f"AZURE_MIGRATED_{uuid.uuid4().hex[:8].upper()}"

            # --- CAPA 3: POSTGRESQL AUDIT CHAIN ---
            async with AsyncSessionLocal() as session:
                available_columns = await self._get_audit_ledger_columns(session)
                
                # Encadenamiento de hashes local
                query_last = text("""
                    SELECT current_hash FROM audit_ledger 
                    WHERE registry_id = :reg_id 
                    ORDER BY created_at DESC LIMIT 1
                """)
                result = await session.execute(query_last, {"reg_id": registry_id})
                row = result.fetchone()
                previous_hash = row[0] if row else "GENESIS_BLOCK"

                local_hash = self.calculate_hash(payload, previous_hash)

                payload_json = json.dumps({
                    **payload,
                    "ledger_provider": self.provider,
                    "gcp_object_path": gcp_object_path,
                    "transaction_id": transaction_id
                })

                insert_columns = ["registry_id", "action", "previous_hash", "current_hash", "payload", "transaction_id"]
                insert_values = [":reg_id", ":action", ":prev_h", ":curr_h", ":payload", ":tx_id"]
                insert_params = {
                    "reg_id": registry_id,
                    "action": action,
                    "prev_h": previous_hash,
                    "curr_h": local_hash,
                    "payload": payload_json,
                    "tx_id": transaction_id,
                }

                # Adaptación dinámica a esquema extendido de base de datos
                if "tenantId" in available_columns:
                    tenant_id = await self._get_default_tenant_id(session)
                    if tenant_id:
                        insert_columns.append('"tenantId"')
                        insert_values.append(":tenant_id")
                        insert_params["tenant_id"] = tenant_id

                if "integrityHash" in available_columns:
                    insert_columns.append('"integrityHash"')
                    insert_values.append(":integrity_hash")
                    insert_params["integrity_hash"] = local_hash
                
                if "resource" in available_columns:
                    insert_columns.append("resource")
                    insert_values.append(":resource")
                    insert_params["resource"] = registry_id
                    
                if "ip" in available_columns:
                    insert_columns.append("ip")
                    insert_values.append(":ip")
                    insert_params["ip"] = payload.get("source_ip") or "system"
                    
                if "userAgent" in available_columns:
                    insert_columns.append('"userAgent"')
                    insert_values.append(":user_agent")
                    insert_params["user_agent"] = "orbital-prime-v26.4"

                query_insert = text(
                    f"INSERT INTO audit_ledger ({', '.join(insert_columns)}) VALUES ({', '.join(insert_values)})"
                )
                await session.execute(query_insert, insert_params)
                await session.commit()
                
            return {"transaction_id": transaction_id, "gcp_path": gcp_object_path}
                
        except Exception as e:
            logger.error(f"Error en Sello Ledger: {str(e)}")
            return {"error": str(e)}

ledger_service = LedgerService()
