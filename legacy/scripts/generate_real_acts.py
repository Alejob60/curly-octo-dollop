import asyncio
from app.services.pdf_service import pdf_service
from app.services.traceability_service import traceability_service
import hashlib
import json
from loguru import logger

async def generate_institutional_samples():
    logger.info("🏛️ Generando muestras reales basadas en el registro 2025 de Cali...")

    CASOS_REALES = [
        {
            "id": "202541310500052362",
            "citizen": "CIUDADANO CATASTRO A",
            "asunto": "SOLICITUD DE INFORMACIÓN DE 3 PREDIOS RURALES",
            "dep": "SUBDIRECCIÓN DE CATASTRO MUNICIPAL",
            "type": "APERTURA"
        },
        {
            "id": "202541310500052322",
            "citizen": "CIUDADANO CATASTRO B",
            "asunto": "PETICIÓN POR INSISTENCIA RAD PADRE 400013399802",
            "dep": "SUBDIRECCIÓN DE CATASTRO MUNICIPAL",
            "type": "REQUERIMIENTO"
        },
        {
            "id": "202541310500053922",
            "citizen": "JUZGADO OCTAVO CIVIL MUNICIPAL",
            "asunto": "TRASLADO POR COMPETENCIA - RADICADO NO 3200SAF-2025-0052825",
            "dep": "SUBDIRECCIÓN DE CATASTRO MUNICIPAL",
            "target": "SECRETARÍA DE GOBIERNO",
            "type": "TRASLADO"
        }
    ]

    for caso in CASOS_REALES:
        logger.info(f"📄 Procesando {caso['type']} para Radicado {caso['id']}")
        
        # 1. Generar Hash de Seguridad Real
        h = hashlib.sha256(f"{caso['id']}|{caso['asunto']}".encode()).hexdigest()
        
        # 2. Generar QR Real
        qr_path = traceability_service.generate_qr_tracking(caso['id'], h)
        
        doc_payload = {
            "radicado": caso['id'],
            "citizen_name": caso['citizen'],
            "content": caso['asunto'],
            "dependency_name": caso['dep'],
            "hash_ledger": h,
            "qr_path": qr_path,
            "target_dependency": caso.get("target", "N/A")
        }

        # 3. Generar el PDF específico según el flujo legal
        if caso['type'] == "APERTURA":
            pdf_path = pdf_service.generate_auto_apertura(doc_payload)
        elif caso['type'] == "REQUERIMIENTO":
            pdf_path = pdf_service.generate_requerimiento_info(doc_payload)
        elif caso['type'] == "TRASLADO":
            pdf_path = pdf_service.generate_traslado_competencia(doc_payload)
        
        logger.success(f"✅ Generado: {pdf_path}")

if __name__ == "__main__":
    asyncio.run(generate_institutional_samples())
