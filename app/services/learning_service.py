import difflib
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorDatabase
import datetime

class LearningService:
    def calculate_similarity(self, text_a: str, text_b: str) -> float:
        """
        LRN-01: Calcula la similitud entre la propuesta de IA y la corrección humana.
        Retorna un score de 0.0 a 1.0.
        """
        if not text_a or not text_b:
            return 0.0
        return difflib.SequenceMatcher(None, text_a, text_b).ratio()

    async def capture_detailed_feedback(self, db: AsyncIOMotorDatabase, data: dict):
        """
        LRN-01/02: Registra el par (IA, Humano) con metadatos de aprendizaje.
        """
        try:
            similarity = self.calculate_similarity(
                data.get("ai_suggestion"), 
                data.get("human_correction")
            )
            
            feedback_entry = {
                "radicado_id": data.get("radicado_id"),
                "funcionario_id": data.get("funcionario_id"),
                "dependencia_id": data.get("dependencia_id"),
                "diagnostico_ia": {
                    "respuesta_original": data.get("ai_suggestion"),
                    "confianza_inicial": data.get("ai_confidence", 0.0)
                },
                "intervencion_humana": {
                    "texto_final": data.get("human_correction"),
                    "comentario": data.get("feedback_comment"),
                    "rating_ia": data.get("rating", 5) # 1-5 estrellas
                },
                "aprendizaje": {
                    "similitud_score": round(similarity, 4),
                    "diferencia_pct": round((1 - similarity) * 100, 2),
                    "es_error_critico": similarity < 0.5,
                    "procesado_para_entrenamiento": False
                },
                "created_at": datetime.datetime.utcnow().isoformat()
            }
            
            await db.feedback_entrenamiento.insert_one(feedback_entry)
            logger.success(f"Feedback detallado capturado para radicado {data.get('radicado_id')}. Similitud: {similarity}")
            return feedback_entry
            
        except Exception as e:
            logger.error(f"Error capturando feedback detallado: {e}")
            return None

learning_service = LearningService()
