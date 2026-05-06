from app.core.db_clients import mongo_db
from loguru import logger
from typing import List, Optional, Dict

class UseCaseService:
    """
    USECASE-2.1: Registry de casos de uso en MongoDB.
    Define las reglas de negocio para tipos específicos de PQRS.
    """
    
    def __init__(self):
        self.collection = mongo_db.use_case_templates

    async def get_all_templates(self) -> List[Dict]:
        cursor = self.collection.find({}, {"_id": 0})
        return await cursor.to_list(length=100)

    async def match_case(self, text: str) -> Optional[Dict]:
        """
        USECASE-2.2: Matcher determinístico.
        Analiza el texto buscando palabras clave y devuelve el template más probable.
        """
        templates = await self.get_all_templates()
        best_match = None
        max_score = 0

        for t in templates:
            score = 0
            keywords = t.get("keywords", [])
            for kw in keywords:
                if kw.lower() in text.lower():
                    score += 1
            
            if score > max_score:
                max_score = score
                best_match = t
        
        if best_match and max_score >= 1:
            logger.info(f"🎯 Caso de Uso detectado: {best_match['display_name']} (Score: {max_score})")
            return best_match
            
        return None

    async def seed_initial_templates(self):
        """Carga los casos de uso maestros alineados con las 28 dependencias."""
        templates = [
            {
                "id": "hacienda_predial",
                "display_name": "Revisión de Impuesto Predial / Valorización",
                "keywords": ["predial", "impuesto", "catastro", "valorización", "pago", "cobro"],
                "required_entities": ["cc", "nombre_completo", "numero_predial"],
                "legal_tags": ["ley_1437_2011", "estatuto_tributario"],
                "mandatory_citations": ["Ley 1437 de 2011 (CPACA): Procedimiento administrativo tributario.", "Estatuto Tributario Municipal de Cali."],
                "dependency_id": "4131",
                "priority": "MEDIA"
            },
            {
                "id": "dagma_ambiental",
                "display_name": "Denuncia Ambiental / Tala / Ruido",
                "keywords": ["tala", "árbol", "escombros", "ruido", "contaminación", "humedal"],
                "required_entities": ["cc", "direccion_hecho", "fotos_evidencia"],
                "legal_tags": ["ley_99_1993", "ley_1333_2009"],
                "mandatory_citations": ["Ley 99 de 1993: Gestión y conservación del medio ambiente.", "Ley 1333 de 2009: Procedimiento sancionatorio ambiental."],
                "dependency_id": "4147",
                "priority": "ALTA"
            },
            {
                "id": "seguridad_policia",
                "display_name": "Queja por Comportamiento Contrario a la Convivencia",
                "keywords": ["policía", "comparendo policía", "vecino", "riña", "establecimiento nocturno"],
                "required_entities": ["cc", "numero_comparendo_policia"],
                "legal_tags": ["ley_1801_2016"],
                "mandatory_citations": ["Ley 1801 de 2016: Código Nacional de Seguridad y Convivencia Ciudadana."],
                "dependency_id": "4137",
                "priority": "MEDIA"
            },
            {
                "id": "fotomulta_gemelo",
                "display_name": "Impugnación por Placa Clonada (Gemelo)",
                "keywords": ["fotomulta", "comparendo", "placa", "clonada", "gemelo", "SIMIT"],
                "required_entities": ["cc", "nombre_completo", "placa", "direccion_notificacion"],
                "legal_tags": ["ley_1843_2017", "sentencia_c038_2020"],
                "mandatory_citations": ["Sentencia C-038 de 2020: Responsabilidad del conductor.", "Ley 1843 de 2017: Fotodetección."],
                "dependency_id": "4134",
                "priority": "ALTA"
            },
            {
                "id": "salud_vital",
                "display_name": "Urgencia Vital / Negación de Servicio",
                "keywords": ["cirugía", "medicamento", "hospital", "clínica", "EPS", "SOAT"],
                "required_entities": ["cc", "nombre_completo", "eps_nombre"],
                "legal_tags": ["ley_1751_2015", "sentencia_t114_19"],
                "mandatory_citations": ["Ley 1751 de 2015: Estatutaria de Salud.", "Principio de Continuidad Jurídica."],
                "dependency_id": "4135",
                "priority": "CRÍTICA"
            }
        ]
        
        for t in templates:
            await self.collection.update_one({"id": t["id"]}, {"$set": t}, upsert=True)
        
        logger.info(f"✅ {len(templates)} Casos de Uso maestros sembrados en MongoDB.")

use_case_service = UseCaseService()
