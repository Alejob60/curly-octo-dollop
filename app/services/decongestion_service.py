from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.sql_models import RadicadoLegacy
from app.core.db_clients import AsyncSessionLocal
from loguru import logger
import hashlib

class DecongestionService:
    async def cluster_by_similarity(self, batch_size: int = 1000):
        """
        BCH-01.4: Agrupa radicados legacy por similitud semántica.
        Permite respuesta masiva a grupos de ciudadanos con el mismo problema.
        """
        logger.info(f"🧬 Iniciando clusterización semántica de {batch_size} registros...")
        
        async with AsyncSessionLocal() as session:
            # 1. Obtener registros pendientes de clusterización
            query = select(RadicadoLegacy).filter_by(cluster_id=None).limit(batch_size)
            result = await session.execute(query)
            records = result.scalars().all()
            
            if not records:
                logger.info("No hay registros pendientes para clusterización.")
                return 0

            # 2. Algoritmo de Agrupación (Normalización y Hashing)
            # Nota: En prod usaríamos embeddings de MongoDB Atlas para esto.
            # Aquí usamos una normalización de texto para la demo.
            clusters_created = set()
            for rec in records:
                # Normalizar asunto: quitar fechas, números y pasar a minúsculas
                normalized = rec.asunto.lower()
                # Extraer "núcleo" del problema (ej: "hueco en la vía", "medicamentos")
                # Simulación de extracción de palabras clave
                keywords = [w for w in normalized.split() if len(w) > 4]
                cluster_key = hashlib.md5(" ".join(sorted(keywords[:3])).encode()).hexdigest()[:8]
                
                rec.cluster_id = f"CLUSTER-{cluster_key.upper()}"
                rec.estado_orbital = "CLUSTERIZADO"
                clusters_created.add(rec.cluster_id)

            await session.commit()
            
        logger.success(f"✅ Agrupación completada. Se crearon {len(clusters_created)} grupos semánticos.")
        return len(clusters_created)

    async def simulate_doc_sync(self, radicado_id: str):
        """
        BCH-01.3: Simula la migración del PDF original de Orfeo a GCS.
        """
        # Generar una URI de Vault segura
        gcs_uri = f"gs://orbital-prime-vault/legacy/{radicado_id}.pdf"
        
        async with AsyncSessionLocal() as session:
            async with session.begin():
                query = update(RadicadoLegacy).where(RadicadoLegacy.orfeo_id == radicado_id).values(gcs_uri=gcs_uri)
                await session.execute(query)
        
        return gcs_uri

decongestion_service = DecongestionService()
