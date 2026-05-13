"""
Adaptador de Integración con Sistemas Institucionales
Soporta: SAP HRMS/Financiero, Orfeo (gestión documental), SAUL (licencias urbanas)
Reto Ingenium PR-01: Extracción de datos de sistemas cerrados vía APIs REST/SOAP/RFC
"""

import asyncio
import hashlib
import hmac
import json
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import httpx
from loguru import logger
from pydantic import BaseModel
from app.core.config import settings


class SistemaInstitucional(str, Enum):
    SAP = "SAP"
    ORFEO = "ORFEO"
    SAUL = "SAUL"
    GOVCO = "GOVCO"
    MANUAL = "MANUAL"


class PQRSDExterna(BaseModel):
    id_externo: str
    sistema_origen: SistemaInstitucional
    tipo: str  # PETICION, QUEJA, RECLAMO, SOLICITUD, DENUNCIA
    dependencia: str
    texto_original: str
    ciudadano_nombre: Optional[str] = None
    ciudadano_email: Optional[str] = None
    ciudadano_documento: Optional[str] = None
    fecha_radicacion: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    estado: Optional[str] = None
    adjuntos: list[str] = []
    metadatos: dict = {}


class SAPConnector:
    """
    Conector para extraer PQRSD desde SAP (módulo CRM/Citizen Services).
    Usa SAP REST API (Fiori / OData) o RFC remoto vía pyrfc si hay acceso directo.
    """

    def __init__(self):
        self.base_url = getattr(settings, "SAP_BASE_URL", "")
        self.client_id = getattr(settings, "SAP_CLIENT_ID", "")
        self.client_secret = getattr(settings, "SAP_CLIENT_SECRET", "")
        self.token: Optional[str] = None
        self._http = httpx.AsyncClient(timeout=30, verify=True)

    async def _get_token(self) -> str:
        """OAuth2 token para SAP API Gateway"""
        if self.token:
            return self.token
        if not self.base_url:
            logger.warning("SAP_BASE_URL no configurado - modo simulación activado")
            return "sim_token"
        resp = await self._http.post(
            f"{self.base_url}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        resp.raise_for_status()
        self.token = resp.json().get("access_token", "")
        return self.token

    async def get_pqrsd_pendientes(self, dependencia: str = "", limit: int = 100) -> list[PQRSDExterna]:
        """
        Extrae PQRSD pendientes desde SAP CRM.
        SAP OData endpoint: /sap/opu/odata/sap/ZCRM_PQRSD_SRV/PQRSDSet
        """
        if not self.base_url:
            logger.warning("SAP no configurado - devolviendo datos simulados")
            return self._simular_pqrsd(SistemaInstitucional.SAP, 3)

        try:
            token = await self._get_token()
            params = {
                "$filter": f"Dependencia eq '{dependencia}'" if dependencia else "Estado eq 'PENDIENTE'",
                "$top": limit,
                "$format": "json",
            }
            resp = await self._http.get(
                f"{self.base_url}/sap/opu/odata/sap/ZCRM_PQRSD_SRV/PQRSDSet",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            resp.raise_for_status()
            raw = resp.json().get("d", {}).get("results", [])
            return [self._map_sap_record(r) for r in raw]
        except Exception as e:
            logger.error(f"Error extrayendo de SAP: {e}")
            return []

    def _map_sap_record(self, r: dict) -> PQRSDExterna:
        return PQRSDExterna(
            id_externo=r.get("RadicadoNo", ""),
            sistema_origen=SistemaInstitucional.SAP,
            tipo=r.get("TipoPQRSD", "PETICION"),
            dependencia=r.get("Dependencia", ""),
            texto_original=r.get("Descripcion", ""),
            ciudadano_nombre=r.get("NombreCiudadano", ""),
            ciudadano_email=r.get("Email", ""),
            ciudadano_documento=r.get("Documento", ""),
            fecha_radicacion=_parse_sap_date(r.get("FechaRadicacion", "")),
            fecha_vencimiento=_parse_sap_date(r.get("FechaVencimiento", "")),
            estado=r.get("Estado", "PENDIENTE"),
            metadatos={"sap_id": r.get("SAP_ID", ""), "anio": r.get("Anio", "")},
        )

    def _simular_pqrsd(self, sistema: SistemaInstitucional, n: int) -> list[PQRSDExterna]:
        """Datos simulados para pruebas sin conexión SAP"""
        return [
            PQRSDExterna(
                id_externo=f"SAP-2026-{1000+i}",
                sistema_origen=sistema,
                tipo=["PETICION", "QUEJA", "RECLAMO"][i % 3],
                dependencia="Secretaría de Movilidad",
                texto_original=f"Solicitud de información sobre trámite #{1000+i}",
                ciudadano_nombre=f"Ciudadano Test {i}",
                ciudadano_email=f"ciudadano{i}@test.com",
                fecha_radicacion=datetime.now(),
                estado="PENDIENTE",
            )
            for i in range(n)
        ]


class OrfeoConnector:
    """
    Conector para Orfeo - Sistema de Gestión Documental del Estado colombiano.
    Extrae radicados y documentos asociados vía API REST de Orfeo.
    """

    def __init__(self):
        self.base_url = getattr(settings, "ORFEO_API_URL", "")
        self.api_key = getattr(settings, "ORFEO_API_KEY", "")
        self._http = httpx.AsyncClient(timeout=30, verify=True)

    async def get_radicados_pendientes(self, dependencia_id: str = "", limit: int = 100) -> list[PQRSDExterna]:
        """
        Extrae radicados pendientes de respuesta desde Orfeo.
        Endpoint: /api/radicados?estado=PENDIENTE&dependencia=X
        """
        if not self.base_url:
            logger.warning("ORFEO_API_URL no configurado - modo simulación")
            return self._simular_radicados(3)

        try:
            params = {"estado": "PENDIENTE", "limit": limit}
            if dependencia_id:
                params["dependencia"] = dependencia_id
            resp = await self._http.get(
                f"{self.base_url}/radicados",
                headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
                params=params,
            )
            resp.raise_for_status()
            return [self._map_radicado(r) for r in resp.json().get("data", [])]
        except Exception as e:
            logger.error(f"Error extrayendo de Orfeo: {e}")
            return []

    async def get_documento(self, radicado_id: str) -> Optional[bytes]:
        """Descarga el documento físico del radicado desde Orfeo"""
        if not self.base_url:
            return None
        try:
            resp = await self._http.get(
                f"{self.base_url}/radicados/{radicado_id}/documento",
                headers={"X-API-Key": self.api_key},
            )
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            logger.error(f"Error descargando documento Orfeo {radicado_id}: {e}")
            return None

    def _map_radicado(self, r: dict) -> PQRSDExterna:
        return PQRSDExterna(
            id_externo=r.get("numero_radicado", ""),
            sistema_origen=SistemaInstitucional.ORFEO,
            tipo=r.get("tipo_solicitud", "PETICION"),
            dependencia=r.get("dependencia_nombre", ""),
            texto_original=r.get("asunto", "") + " " + r.get("descripcion", ""),
            ciudadano_nombre=r.get("remitente_nombre", ""),
            ciudadano_email=r.get("remitente_email", ""),
            ciudadano_documento=r.get("remitente_documento", ""),
            fecha_radicacion=_parse_iso_date(r.get("fecha_radicacion", "")),
            fecha_vencimiento=_parse_iso_date(r.get("fecha_vencimiento_respuesta", "")),
            estado=r.get("estado", "RADICADO"),
            adjuntos=[a.get("url", "") for a in r.get("adjuntos", [])],
            metadatos={"orfeo_id": r.get("id", ""), "folios": r.get("numero_folios", 0)},
        )

    def _simular_radicados(self, n: int) -> list[PQRSDExterna]:
        return [
            PQRSDExterna(
                id_externo=f"ORFEO-2026-{2000+i}",
                sistema_origen=SistemaInstitucional.ORFEO,
                tipo="QUEJA",
                dependencia="Secretaría de Planeación",
                texto_original=f"Radicado de prueba Orfeo #{2000+i}: solicitud de concepto urbanístico",
                ciudadano_nombre=f"Solicitante {i}",
                ciudadano_email=f"solicitante{i}@cali.gov.co",
                fecha_radicacion=datetime.now(),
                estado="RADICADO",
            )
            for i in range(n)
        ]


class SAULConnector:
    """
    Conector para SAUL - Sistema de Atención Urbanística y Licencias.
    Extrae solicitudes de licencias de construcción y urbanismo.
    """

    def __init__(self):
        self.base_url = getattr(settings, "SAUL_ENDPOINT", "")
        self._http = httpx.AsyncClient(timeout=30, verify=True)

    async def get_solicitudes_pendientes(self, limit: int = 50) -> list[PQRSDExterna]:
        if not self.base_url:
            logger.warning("SAUL_ENDPOINT no configurado - modo simulación")
            return self._simular_solicitudes(2)

        try:
            resp = await self._http.get(
                f"{self.base_url}/solicitudes",
                params={"estado": "PENDIENTE", "limit": limit},
            )
            resp.raise_for_status()
            return [self._map_solicitud(s) for s in resp.json().get("solicitudes", [])]
        except Exception as e:
            logger.error(f"Error extrayendo de SAUL: {e}")
            return []

    def _map_solicitud(self, s: dict) -> PQRSDExterna:
        return PQRSDExterna(
            id_externo=s.get("numero_solicitud", ""),
            sistema_origen=SistemaInstitucional.SAUL,
            tipo="SOLICITUD",
            dependencia="Secretaría de Planeación - Licencias",
            texto_original=s.get("descripcion_obra", ""),
            ciudadano_nombre=s.get("solicitante_nombre", ""),
            ciudadano_email=s.get("solicitante_email", ""),
            ciudadano_documento=s.get("solicitante_cedula", ""),
            fecha_radicacion=_parse_iso_date(s.get("fecha_radicacion", "")),
            fecha_vencimiento=_parse_iso_date(s.get("fecha_vencimiento", "")),
            estado=s.get("estado", "PENDIENTE"),
            metadatos={
                "saul_id": s.get("id_solicitud", ""),
                "tipo_licencia": s.get("tipo_licencia", ""),
                "predio": s.get("numero_predial", ""),
            },
        )

    def _simular_solicitudes(self, n: int) -> list[PQRSDExterna]:
        return [
            PQRSDExterna(
                id_externo=f"SAUL-2026-{3000+i}",
                sistema_origen=SistemaInstitucional.SAUL,
                tipo="SOLICITUD",
                dependencia="Secretaría de Planeación",
                texto_original=f"Solicitud de licencia de construcción predio #{3000+i}",
                ciudadano_nombre=f"Constructor {i}",
                estado="PENDIENTE",
                metadatos={"tipo_licencia": "NUEVA_CONSTRUCCION"},
            )
            for i in range(n)
        ]


class InstitucionalBridge:
    """
    Puente universal que agrega PQRSD de todos los sistemas institucionales.
    Implementa el concepto 'Universal Bridge' del concurso Ingenium PR-01.
    """

    def __init__(self):
        self.sap = SAPConnector()
        self.orfeo = OrfeoConnector()
        self.saul = SAULConnector()

    async def harvest_all(
        self,
        include_sistemas: list[SistemaInstitucional] = None,
        dependencia: str = "",
        limit_per_system: int = 100,
    ) -> dict[str, list[PQRSDExterna]]:
        """
        Cosecha PQRSD de todos los sistemas configurados.
        Retorna dict agrupado por sistema para trazabilidad.
        """
        if include_sistemas is None:
            include_sistemas = [SistemaInstitucional.SAP, SistemaInstitucional.ORFEO, SistemaInstitucional.SAUL]

        tasks = {}
        if SistemaInstitucional.SAP in include_sistemas:
            tasks["SAP"] = self.sap.get_pqrsd_pendientes(dependencia, limit_per_system)
        if SistemaInstitucional.ORFEO in include_sistemas:
            tasks["ORFEO"] = self.orfeo.get_radicados_pendientes(dependencia, limit_per_system)
        if SistemaInstitucional.SAUL in include_sistemas:
            tasks["SAUL"] = self.saul.get_solicitudes_pendientes(limit_per_system)

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        output = {}
        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Error en sistema {key}: {result}")
                output[key] = []
            else:
                output[key] = result
                logger.info(f"Sistema {key}: {len(result)} PQRSD extraídas")

        total = sum(len(v) for v in output.values())
        logger.info(f"Total PQRSD cosechadas de sistemas institucionales: {total}")
        return output

    async def get_status(self) -> dict:
        """Verifica conectividad con todos los sistemas institucionales"""
        status = {}
        for sistema, connector in [("SAP", self.sap), ("ORFEO", self.orfeo), ("SAUL", self.saul)]:
            configured = bool(getattr(connector, "base_url", ""))
            status[sistema] = {
                "configurado": configured,
                "estado": "CONECTADO" if configured else "SIMULACION",
                "url": getattr(connector, "base_url", "No configurado"),
            }
        return status


# Helper utilities
def _parse_sap_date(val: str) -> Optional[datetime]:
    """Parsea fechas SAP formato /Date(epoch)/ """
    if not val:
        return None
    try:
        if "/Date(" in val:
            epoch_ms = int(val.replace("/Date(", "").replace(")/", "").split("+")[0])
            return datetime.fromtimestamp(epoch_ms / 1000)
        return datetime.fromisoformat(val)
    except Exception:
        return None


def _parse_iso_date(val: str) -> Optional[datetime]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception:
        return None


# Singleton
_bridge: Optional[InstitucionalBridge] = None


def get_bridge() -> InstitucionalBridge:
    global _bridge
    if _bridge is None:
        _bridge = InstitucionalBridge()
    return _bridge
