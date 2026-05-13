"""
Endpoint público para verificación de radicados vía QR V64.2
✅ Sincronizado con pdf_paths | ✅ Tabla de documentos dinámica | ✅ Trazabilidad
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from app.core.db_clients import postgres_manager
from app.models.sql_models import CaseRegistry, AuditLedger
from sqlalchemy import select
from datetime import datetime, timedelta
import hashlib
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/verify", tags=["verification"])

@router.get("/{radicado}", response_class=HTMLResponse)
async def verify_radicado(
    radicado: str,
    request: Request,
    hash: str = Query(..., description="SHA-256 hash del radicado para validación")
):
    """
    Página pública de verificación de radicado.
    Muestra estado actual + documentos generados + línea de tiempo.
    """
    # 1. Validar hash
    expected_hash = hashlib.sha256(radicado.encode()).hexdigest()
    if hash != expected_hash:
        logger.warning(f"🛑 Intento de verificación fallido para {radicado}")
        return HTMLResponse(content=_render_error_page("Código de verificación inválido."), status_code=403)
    
    # 2. Consultar DB
    async with postgres_manager.get_session() as session:
        stmt = select(CaseRegistry).where(CaseRegistry.radicado == radicado)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        
        if not record:
            return HTMLResponse(content=_render_error_page(f"El radicado {radicado} no existe en nuestra base de datos."), status_code=404)

        # Cargar documentos desde pdf_paths (JSON en SQL)
        docs_list = []
        if record.pdf_paths:
            for d_type, d_url in record.pdf_paths.items():
                docs_list.append({
                    "type": d_type.replace('_', ' ').upper(),
                    "url": d_url,
                    "name": str(d_url).split('/')[-1]
                })

        public_data = {
            "radicado": record.radicado,
            "estado_label": _get_status_label(record.estado),
            "created_at": record.created_at.strftime("%d/%m/%Y %H:%M"),
            "estimated_response": (record.created_at + timedelta(days=15)).strftime("%d de %B, %Y"),
            "documents": docs_list,
            "dependencia": record.dependencia_nombre or "Secretaría General"
        }
        
        return HTMLResponse(content=_render_verification_page(public_data))

def _get_status_label(db_status: str) -> str:
    mapping = {
        "INICIADO": "📥 RECIBIDO",
        "ANALIZADO": "🔍 EN ANÁLISIS JURÍDICO",
        "EN_PROCESO": "🤖 PROCESANDO DOCUMENTOS",
        "APPROVED": "✅ EXPEDIENTE SELLADO",
        "LEGACY_SYNCED": "📤 NOTIFICADO OFICIALMENTE"
    }
    return mapping.get(db_status, "🔄 EN TRÁMITE")

def _render_error_page(msg: str) -> str:
    return f"""
    <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1 style="color: #e11d48;">⚠️ Error de Verificación</h1>
        <p>{msg}</p>
        <a href="/">Volver al portal</a>
    </body></html>
    """

def _render_verification_page(data: dict) -> str:
    docs_html = "".join([f'''
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 15px; background: white; border: 1px solid #e2e8f0; border-radius: 12px; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 24px;">📄</span>
                <div>
                    <div style="font-size: 13px; font-weight: 800; color: #1e293b;">{d['type']}</div>
                    <div style="font-size: 10px; color: #64748b;">{d['name']}</div>
                </div>
            </div>
            <a href="{d['url']}" target="_blank" style="background: #2563eb; color: white; text-decoration: none; padding: 8px 16px; border-radius: 8px; font-size: 11px; font-weight: 700;">VER PDF</a>
        </div>
    ''' for d in data['documents']]) or '<p style="text-align: center; color: #94a3b8; font-size: 13px;">No hay documentos adjuntos en este radicado.</p>'

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Consulta de Radicado | Alcaldía de Cali</title>
        <style>
            body {{ font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 20px; background: #f1f5f9; color: #1e293b; }}
            .card {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 24px; padding: 32px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; border-bottom: 2px solid #f8fafc; padding-bottom: 20px; margin-bottom: 24px; }}
            .badge {{ background: #fef3c7; color: #92400e; padding: 6px 12px; border-radius: 9999px; font-size: 10px; font-weight: 800; display: inline-block; margin-bottom: 8px; }}
            .radicado-box {{ background: #0f172a; color: #38bdf8; padding: 12px; border-radius: 12px; font-family: monospace; font-size: 18px; font-weight: bold; }}
            .section-title {{ font-size: 11px; font-weight: 800; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 16px; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <div class="badge">SISTEMA ORBITAL PRIME</div>
                <div style="font-size: 18px; font-weight: 900; margin-bottom: 12px;">🏛️ Alcaldía de Santiago de Cali</div>
                <div class="radicado-box">{data['radicado']}</div>
                <div style="margin-top: 16px; font-weight: 800; color: #2563eb; font-size: 14px;">{data['estado_label']}</div>
            </div>
            
            <div style="background: #f8fafc; padding: 20px; border-radius: 16px; border: 1px solid #e2e8f0; font-size: 13px;">
                <div style="margin-bottom: 8px;"><strong>Dependencia:</strong> {data['dependencia']}</div>
                <div style="margin-bottom: 8px;"><strong>Fecha Radicación:</strong> {data['created_at']}</div>
                <div><strong>Respuesta Estimada:</strong> {data['estimated_response']}</div>
            </div>

            <div class="section-title">Documentos del Expediente</div>
            {docs_html}

            <div style="margin-top: 32px; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 24px;">
                <p style="font-size: 10px; color: #94a3b8; line-height: 1.5;">
                    🔒 Registro Certificado por <strong>Bóveda Digital Orbital</strong>.<br>
                    Cualquier alteración de este registro invalida el documento oficial.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
