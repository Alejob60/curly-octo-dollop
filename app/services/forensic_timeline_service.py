from typing import List, Dict, Any
from app.core.db_clients import AsyncSessionLocal
from sqlalchemy import text
import json
from loguru import logger

class ForensicTimelineService:
    """
    V56.2: Servicio de Reconstrucción de Línea de Tiempo Forense.
    Recupera eventos del Audit Ledger y Trazabilidad para visualización E2E.
    """

    async def get_case_timeline(self, radicado: str) -> List[Dict[str, Any]]:
        """
        Recupera todos los eventos asociados a un radicado, ordenados cronológicamente.
        """
        timeline = []
        
        async with AsyncSessionLocal() as session:
            try:
                # 1. Recuperar eventos del Audit Ledger (Inmutables)
                query_ledger = text("""
                    SELECT action, payload, transaction_id, created_at, current_hash
                    FROM audit_ledger
                    WHERE registry_id = :rad
                    ORDER BY created_at ASC
                """)
                res_ledger = await session.execute(query_ledger, {"rad": radicado})
                
                for row in res_ledger:
                    payload = row[1]
                    if isinstance(payload, str):
                        try: payload = json.loads(payload)
                        except: pass
                    
                    timeline.append({
                        "type": "FORENSIC",
                        "action": row[0],
                        "details": payload,
                        "tx_id": row[2],
                        "timestamp": row[3].isoformat(),
                        "integrity_hash": row[4][:16].upper() if row[4] else None
                    })

                # 2. Recuperar eventos de Trazabilidad (Estado)
                query_traz = text("""
                    SELECT estado_anterior, estado_nuevo, id_funcionario, fecha_cambio, comentario
                    FROM trazabilidad_logs
                    WHERE radicado_id = (SELECT id FROM radicados WHERE codigo_radicado = :rad)
                    ORDER BY fecha_cambio ASC
                """)
                # Nota: Esta query asume que radicado_id en trazabilidad_logs apunta al ID entero de radicados.
                # Si no hay match, simplemente no añade eventos de trazabilidad.
                try:
                    res_traz = await session.execute(query_traz, {"rad": radicado})
                    for row in res_traz:
                        timeline.append({
                            "type": "STATE_CHANGE",
                            "action": f"TRANSITION: {row[0]} -> {row[1]}",
                            "official": row[2],
                            "timestamp": row[3].isoformat(),
                            "comment": row[4]
                        })
                except Exception as e:
                    logger.warning(f"No se pudo recuperar trazabilidad para {radicado}: {e}")

                # 3. Ordenar todo por timestamp
                timeline.sort(key=lambda x: x["timestamp"])
                
                return timeline

            except Exception as e:
                logger.error(f"Error reconstruyendo línea de tiempo para {radicado}: {e}")
                return []

forensic_timeline_service = ForensicTimelineService()
