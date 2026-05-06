#!/usr/bin/env python3
"""
🔍 ORBITAL PRIME - DIAGNÓSTICO AUTOMÁTICO DE FLUJO E2E
Verifica: Tipos de datos + Grounding jurídico + Enrutamiento correcto
"""

import json
import re
import asyncio
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from loguru import logger
from enum import Enum

class DiagnosticStatus(Enum):
    PASS = "✅ PASS"
    WARNING = "⚠️ WARNING"
    FAIL = "❌ FAIL"

@dataclass
class DiagnosticResult:
    status: DiagnosticStatus
    message: str
    details: Dict
    recommendations: List[str]

class FlowDiagnosticChecker:
    """
    Diagnóstico automático del flujo PQRSD antes de generación de PDFs.
    Detecta: tipos incorrectos, grounding vacío, enrutamiento erróneo.
    """
    
    # Mapeo de keywords → dependency_id esperado
    KEYWORD_ROUTING_MAP = {
        "comparendo": "4152", "fotomulta": "4152", "tránsito": "4152", "movilidad": "4152",
        "salud": "4135", "eps": "4135", "médico": "4135", "vacuna": "4135",
        "educación": "2201", "colegio": "2201", "escuela": "2201",
        "hueco": "4146", "vía": "4146", "pavimento": "4146", "infraestructura": "4146",
        "basuras": "4147", "poda": "4147", "ambiental": "4147",
        "jac": "4142", "junta": "4142", "comunal": "4142", "social": "4142"
    }
    
    # Leyes mínimas esperadas por dependencia
    MIN_LAWS_BY_DEP = {
        "4152": ["Ley 769 de 2002", "Ley 1843 de 2017"],  # Movilidad
        "4135": ["Ley 1751 de 2015", "Ley 1098 de 2006"],  # Salud
        "2201": ["Ley 115 de 1994", "Ley 1620 de 2013"],   # Educación
        "4146": ["Ley 769 de 2002", "Ley 1755 de 2015"],   # Infraestructura
        "4147": ["Ley 99 de 1993", "Ley 1755 de 2015"],    # Ambiente
        "4142": ["Ley 489 de 1998", "Ley 743 de 2002"],    # Desarrollo Social
    }
    
    # Campos críticos con tipos esperados
    CRITICAL_FIELDS = {
        "citas_verificables": list,
        "hechos_extraidos": str,
        "soporte_traslado": str,
        "borrador_proyeccion": str,
        "dependencia_id": str,
        "radicado": str
    }
    
    # Longitudes mínimas para campos de texto
    MIN_LENGTHS = {
        "hechos_extraidos": 150,
        "soporte_traslado": 100,
        "borrador_proyeccion": 120
    }
    
    async def run_full_diagnostic(self, context: Dict, raw_message: str = "") -> List[DiagnosticResult]:
        """Ejecuta todos los checks y retorna lista de resultados"""
        results = []
        
        # 1. Check de tipos de datos
        results.append(self._check_data_types(context))
        
        # 2. Check de grounding jurídico
        results.append(await self._check_grounding(context))
        
        # 3. Check de enrutamiento
        results.append(self._check_routing(context, raw_message))
        
        # 4. Check de longitud de campos críticos
        results.append(self._check_field_lengths(context))
        
        # 5. Check de consistencia de radicado
        results.append(self._check_radicado_consistency(context))
        
        # Resumen
        fail_count = sum(1 for r in results if r.status == DiagnosticStatus.FAIL)
        warn_count = sum(1 for r in results if r.status == DiagnosticStatus.WARNING)
        
        if fail_count > 0:
            logger.error(f"🚨 DIAGNÓSTICO FALLÓ: {fail_count} errores críticos")
        elif warn_count > 0:
            logger.warning(f"⚠️ DIAGNÓSTICO CON ADVERTENCIAS: {warn_count} advertencias")
        else:
            logger.success("✅ DIAGNÓSTICO EXITOSO: Todos los checks pasaron")
            
        return results
    
    def _check_data_types(self, context: Dict) -> DiagnosticResult:
        """Verifica que los campos críticos tengan el tipo de dato correcto"""
        errors = []
        warnings = []
        
        for field, expected_type in self.CRITICAL_FIELDS.items():
            value = context.get(field)
            
            if value is None:
                errors.append(f"Campo '{field}' es None (esperado {expected_type.__name__})")
                continue
                
            if not isinstance(value, expected_type):
                if field == "citas_verificables" and isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            warnings.append(f"Campo '{field}' es string JSON, se parseará automáticamente")
                            continue
                    except:
                        pass
                errors.append(f"Tipo incorrecto en '{field}': {type(value).__name__} != {expected_type.__name__}")
        
        status = DiagnosticStatus.FAIL if errors else (DiagnosticStatus.WARNING if warnings else DiagnosticStatus.PASS)
        return DiagnosticResult(status, "Validación de tipos de datos", {"errors": errors, "warnings": warnings}, [])

    async def _check_grounding(self, context: Dict) -> DiagnosticResult:
        """Verifica que el grounding jurídico sea adecuado"""
        errors = []
        warnings = []
        citations = context.get("citas_verificables", [])
        
        if isinstance(citations, str):
            try: citations = json.loads(citations)
            except: citations = []
        
        if not citations:
            errors.append("No hay citas legales en citas_verificables")
        else:
            for i, cit in enumerate(citations):
                if not isinstance(cit, dict):
                    errors.append(f"Cita {i} no es un diccionario")
                    continue
                missing = [k for k in ["citacion_formato", "articulo", "texto_relevante"] if k not in cit]
                if missing: errors.append(f"Cita {i} falta campos: {missing}")

        dep_id = context.get("dependencia_id", "")
        expected_laws = self.MIN_LAWS_BY_DEP.get(dep_id, [])
        found_laws = [str(c.get("citacion_formato", "")) for c in citations if isinstance(c, dict)]
        
        missing_expected = [law for law in expected_laws if not any(law in found for found in found_laws)]
        if missing_expected:
            warnings.append(f"Leyes esperadas no encontradas para {dep_id}: {missing_expected}")
        
        status = DiagnosticStatus.FAIL if errors else (DiagnosticStatus.WARNING if warnings else DiagnosticStatus.PASS)
        return DiagnosticResult(status, "Validación de grounding jurídico", {"errors": errors, "warnings": warnings}, [])

    def _check_routing(self, context: Dict, raw_message: str = "") -> DiagnosticResult:
        """Verifica que el enrutamiento a dependencia sea correcto"""
        errors = []
        warnings = []
        dep_id = context.get("dependencia_id", "")
        message = raw_message.lower()
        
        if not dep_id or dep_id == "4131":
            matched = [kw for kw in self.KEYWORD_ROUTING_MAP if kw in message]
            if matched:
                warnings.append(f"Keywords detectadas {matched} podrían requerir ruteo específico (actual: {dep_id})")
        
        status = DiagnosticStatus.WARNING if warnings else DiagnosticStatus.PASS
        return DiagnosticResult(status, "Validación de enrutamiento", {"warnings": warnings}, [])

    def _check_field_lengths(self, context: Dict) -> DiagnosticResult:
        """Verifica que los campos de texto tengan longitud mínima"""
        errors = []
        for field, min_len in self.MIN_LENGTHS.items():
            value = str(context.get(field, ""))
            if len(value) < min_len:
                errors.append(f"Campo '{field}' muy corto: {len(value)} < {min_len}")
        
        status = DiagnosticStatus.FAIL if errors else DiagnosticStatus.PASS
        return DiagnosticResult(status, "Validación de longitud de campos", {"errors": errors}, [])

    def _check_radicado_consistency(self, context: Dict) -> DiagnosticResult:
        """Verifica consistencia del radicado"""
        radicado = context.get("radicado", "")
        if not radicado or "CALI" not in radicado:
            return DiagnosticResult(DiagnosticStatus.FAIL, "Radicado inválido", {"radicado": radicado}, [])
        return DiagnosticResult(DiagnosticStatus.PASS, "Radicado válido", {"radicado": radicado}, [])

    def generate_report(self, results: List[DiagnosticResult]) -> str:
        """Genera reporte legible de diagnóstico"""
        lines = ["\n" + "="*60, "🔍 REPORTE DE DIAGNÓSTICO DE FLUJO E2E", "="*60]
        for r in results:
            lines.append(f"{r.status.value} {r.message}")
            if r.details.get("errors"):
                for e in r.details["errors"]: lines.append(f"   ❌ {e}")
            if r.details.get("warnings"):
                for w in r.details["warnings"]: lines.append(f"   ⚠️ {w}")
        
        fail_count = sum(1 for r in results if r.status == DiagnosticStatus.FAIL)
        lines.append("-" * 60)
        if fail_count > 0: lines.append(f"🚨 BLOQUEO: {fail_count} errores críticos detectados.")
        else: lines.append("✅ FLUJO VALIDADO. Proceder con generación.")
        return "\n".join(lines)

async def validate_context_before_pdf_generation(context: Dict, raw_message: str = "") -> bool:
    checker = FlowDiagnosticChecker()
    results = await checker.run_full_diagnostic(context, raw_message)
    report = checker.generate_report(results)
    logger.info(report)
    return not any(r.status == DiagnosticStatus.FAIL for r in results)

if __name__ == "__main__":
    test_context = {
        "radicado": "CALI-GEN-TEST01",
        "dependencia_id": "4152",
        "hechos_extraidos": "El ciudadano solicita nulidad..." * 20,
        "soporte_traslado": "Motivación técnica..." * 10,
        "borrador_proyeccion": "Respuesta de fondo..." * 15,
        "citas_verificables": [{"citacion_formato": "Ley 769 de 2002", "articulo": "131", "texto_relevante": "Texto largo de prueba..."}]
    }
    asyncio.run(validate_context_before_pdf_generation(test_context, "comparendo"))
