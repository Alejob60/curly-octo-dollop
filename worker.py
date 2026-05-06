from app.tasks.pqrsd_tasks import celery_app
from loguru import logger

# Punto de entrada para el worker Celery
if __name__ == "__main__":
    logger.info("Iniciando Celery Worker para GovDocs Engine...")
    celery_app.start()
