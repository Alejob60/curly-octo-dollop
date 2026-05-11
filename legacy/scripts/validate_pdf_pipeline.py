# scripts/validate_pdf_pipeline.py
import asyncio
import json
from loguru import logger

# Simulación del contexto que debería venir del Manager
MOCK_CONTEXT = {
    "radicado": "CALI-GEN-TEST-001",
    "dependencia_gestora": "SECRETARÍA DE DESARROLLO TERRITORIAL",
    "hechos_extraidos": "El señor Eduardo Hurtado Sánchez, de la JAC Calimio Decepaz, solicita jornada de capacitación en manipulación de alimentos para el 24 de oct 2025.",
    "tipo_solicitud": "Petición",
    "fecha_generacion": "26/04/2026",
    "citas_verificables": [
        {
            "citacion_formato": "Resolución 2674 de 2013",
            "articulo": "12",
            "texto_relevante": "El personal manipulador de alimentos debe recibir capacitación en educación sanitaria...",
            "ente_emisor": "Ministerio de Salud",
            "vigencia_desde": "2013"
        },
        {
            "citacion_formato": "Ley 743 de 2002",
            "articulo": "3",
            "texto_relevante": "Promover el desarrollo integral del individuo y de la comunidad...",
            "ente_emisor": "Congreso",
            "vigencia_desde": "2002"
        }
    ]
}

async def validate_context():
    logger.info("🔍 Iniciando validación de contexto para PDFs...")
    
    required_keys = ["radicado", "hechos_extraidos", "citas_verificables", "dependencia_gestora"]
    missing = [k for k in required_keys if k not in MOCK_CONTEXT]
    
    if missing:
        logger.error(f"❌ FALLO CRÍTICO: Faltan claves en el contexto: {missing}")
        return False
    
    if len(MOCK_CONTEXT["hechos_extraidos"]) < 20:
        logger.error("❌ FALLO: 'hechos_extraidos' es demasiado corto o está vacío.")
        return False
        
    if not MOCK_CONTEXT["citas_verificables"] or len(MOCK_CONTEXT["citas_verificables"]) == 0:
        logger.warning("⚠️ ADVERTENCIA: No hay citas legales ('citas_verificables'). El Grounding fallará.")
    
    logger.success("✅ Contexto válido. Listo para inyectar en Jinja2.")
    return True

if __name__ == "__main__":
    asyncio.run(validate_context())
