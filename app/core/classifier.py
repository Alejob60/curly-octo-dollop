from app.schemas.mapping import CaliDependency, DEPENDENCY_NAMES
import numpy as np
from loguru import logger
from app.core.azure_openai_client import get_text_embedding

class CaliRouter:
    def __init__(self):
        # Generamos embeddings precalculados de las dependencias para comparación rápida
        try:
            self.dep_embeddings = self._precompute_embeddings()
        except Exception as e:
            logger.error(f"No fue posible precalcular embeddings de dependencias: {e}")
            self.dep_embeddings = {}

    def _precompute_embeddings(self):
        """Precalcula los vectores de los nombres de las secretarías."""
        embeddings = {}
        for dep_id, dep_name in DEPENDENCY_NAMES.items():
            embeddings[dep_id] = get_text_embedding(dep_name)
        return embeddings

    async def get_target_dependency(self, content: str) -> str:
        """Asigna la dependencia por similitud de coseno entre el texto y la misión de la secretaría."""
        try:
            if not self.dep_embeddings:
                return CaliDependency.GENERAL.value

            content_vec = get_text_embedding(content[:1000])
            
            best_match = None
            highest_sim = -1
            
            for dep_id, dep_vec in self.dep_embeddings.items():
                sim = np.dot(content_vec, dep_vec) / (np.linalg.norm(content_vec) * np.linalg.norm(dep_vec))
                if sim > highest_sim:
                    highest_sim = sim
                    best_match = dep_id
            
            logger.info(f"🎯 Clasificación semántica: {best_match} (Similitud: {highest_sim:.2f})")
            return best_match.value
        except Exception as e:
            logger.error(f"Error en clasificación: {str(e)}")
            return CaliDependency.GENERAL.value

cali_router = CaliRouter()
