from google.cloud import pubsub_v1
from app.core.config import settings
from app.bridge.adapters import institutional_bridge
from app.services.persistence_bridge import persistence_bridge
from loguru import logger
import json
import asyncio

class OrfeoSyncWorker:
    """
    V60.2: Trabajador de Sincronización Masiva vía Pub/Sub.
    Garantiza que cada cierre en Orbital Prime se refleje en Orfeo/SAUL.
    """

    def __init__(self):
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(
            settings.GCP_PROJECT_ID, "orfeo-sync-sub"
        )

    async def start_listening(self):
        """Inicia el bucle de escucha de eventos de finalización."""
        logger.info(f"🛰️ [WORKER] Escuchando eventos en {self.subscription_path}...")
        
        def callback(message):
            try:
                data = json.loads(message.data.decode("utf-8"))
                logger.info(f"📥 [EVENT] Recibido evento de sincronización para {data.get('radicado')}")
                
                # Sincronización Real con Orfeo
                asyncio.run(institutional_bridge.create_orfeo_entry(data))
                
                message.ack()
                logger.success(f"✅ [SYNC] Radicado {data.get('radicado')} sincronizado con éxito.")
            except Exception as e:
                logger.error(f"❌ [WORKER_ERROR] Fallo al procesar mensaje: {e}")
                # Nack para reintento si es crítico
                message.nack()

        # Iniciamos el streaming pull
        streaming_pull_future = self.subscriber.subscribe(self.subscription_path, callback=callback)
        
        with self.subscriber:
            try:
                # Mantener vivo el hilo
                streaming_pull_future.result()
            except Exception as e:
                logger.error(f"⚠️ Worker detenido inesperadamente: {e}")
                streaming_pull_future.cancel()

orfeo_sync_worker = OrfeoSyncWorker()
