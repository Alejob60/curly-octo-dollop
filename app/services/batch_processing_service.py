import asyncio
from loguru import logger
from app.services.pdf_service import pdf_service
from app.services.signature_service import signature_service
from app.services.vault_manager import vault_manager
from app.models.sql_models import RadicadoLegacy
from app.core.db_clients import AsyncSessionLocal
from sqlalchemy import select
import os

class BatchProcessingService:
    async def process_cluster_in_batch(self, cluster_id: str, official_data: dict):
        """
        BCH-05: Generación Masiva de Actos Administrativos por Cluster.
        Evacua cientos de casos con una sola firma del Secretario.
        """
        logger.info(f"⚡ Iniciando FIRMA MASIVA para el cluster: {cluster_id}")
        
        async with AsyncSessionLocal() as session:
            # 1. Obtener todos los radicados de ese grupo
            query = select(RadicadoLegacy).filter_by(cluster_id=cluster_id)
            result = await session.execute(query)
            records = result.scalars().all()
            
            if not records:
                logger.warning("No se encontraron registros en este cluster.")
                return 0

            processed_count = 0
            for rec in records:
                # 2. Crear Vault para cada uno
                paths = vault_manager.create_radicado_container(rec.orfeo_id, "CIUDADANO_LEGACY")
                
                # 3. Generar Sello Digital
                h_ledger = signature_service.generate_electronic_signature(rec.asunto, official_data["id"])
                
                # 4. Generar Respuesta de Alta Fidelidad (Usando la respuesta modelo)
                doc_payload = {
                    "radicado": rec.orfeo_id,
                    "radicado_entrada": rec.orfeo_id,
                    "citizen_name": "CIUDADANO REGISTRADO EN ORFEO",
                    "citizen_address": "Dirección en Expediente",
                    "topic": "Respuesta Masiva de Descongestión",
                    "antecedents": f"Se analiza el radicado histórico {rec.orfeo_id} referente a: {rec.asunto}",
                    "legal_analysis": official_data["legal_base"],
                    "conclusion": "SE RESUELVE: Atender la solicitud bajo los términos de la jornada de descongestión 2026.",
                    "official_name": official_data["name"],
                    "official_title": official_data["title"],
                    "hash_ledger": h_ledger,
                    "dependency_name": rec.dependencia_orfeo or "SECRETARÍA GENERAL"
                }
                
                pdf_path = pdf_service.generate_official_response_v6(doc_payload, paths)
                
                if pdf_path:
                    rec.estado_orbital = "RESUELTO_MASIVO"
                    rec.gcs_uri = pdf_path
                    processed_count += 1
            
            await session.commit()
            
        logger.success(f"🏆 OPERACIÓN EXITOSA: Se han firmado y generado {processed_count} respuestas para el cluster {cluster_id}")
        return processed_count

batch_processor = BatchProcessingService()
