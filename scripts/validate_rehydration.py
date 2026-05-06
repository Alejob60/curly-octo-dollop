#!/usr/bin/env python3
"""
Validación automática de rehidratación completa en casos de prueba.
Ejecutar después de aplicar los fixes.
"""

import asyncio
import json
import re
from pathlib import Path

async def validate_case(session_id: str, expected_fields: dict) -> bool:
    """Valida que un caso procesado no tenga tokens pendientes"""
    
    # Cargar contexto desde DB (simulado)
    context_path = Path(f"output/{session_id}_context.json")
    if not context_path.exists():
        print(f"❌ {session_id}: Contexto no encontrado")
        return False
    
    with open(context_path) as f:
        context = json.load(f)
    
    # Validar campos críticos
    errors = []
    for field in ["borrador_proyeccion", "hechos_extraidos"]:
        value = context.get(field, "")
        if isinstance(value, str):
            # Buscar tokens [MAYUSCULA_NUM] no permitidos
            tokens = re.findall(r'\[[A-Z_0-9ÁÉÍÓÚÑ]+\]', value)
            allowed = ["[Día]", "[Mes]", "[Año]"]
            forbidden = [t for t in tokens if t not in allowed]
            if forbidden:
                errors.append(f"{field}: {forbidden}")
    
    # Validar valores esperados
    for field, expected in expected_fields.items():
        actual = context.get(field, "")
        if expected and expected not in str(actual):
            errors.append(f"{field}: esperado '{expected}', obtenido '{actual[:50]}...'")
    
    if errors:
        print(f"❌ {session_id}: {errors}")
        return False
    
    print(f"✅ {session_id}: Rehidratación completa")
    return True


async def main():
    """Ejecutar validación en casos de prueba"""
    
    test_cases = [
        {
            "session_id": "test_capacitacion",
            "expected": {
                "nombres": "Eduardo",
                "apellidos": "Hurtado Sánchez",
                "radicado": "CALI-GEN-",
            }
        },
        {
            "session_id": "test_infraestructura", 
            "expected": {
                "nombres": "Alejandro",
                "dependencia_gestora": "Secretaría de Infraestructura",
            }
        },
        {
            "session_id": "test_comparendo",
            "expected": {
                "nombres": "Alejandro",
                "dependencia_gestora": "Secretaría de Movilidad",
            }
        },
    ]
    
    results = []
    for case in test_cases:
        result = await validate_case(case["session_id"], case["expected"])
        results.append(result)
    
    # Resumen
    passed = sum(results)
    print(f"
📊 Resumen: {passed}/{len(results)} casos válidos")
    
    if passed == len(results):
        print("🎉 Todos los casos pasaron validación de rehidratación")
        return 0
    else:
        print("⚠️ Algunos casos requieren revisión")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
