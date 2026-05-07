# 🛠️ REPAIR LOG - ORBITAL PRIME

| Fecha | Ticket | Archivo | Problema | Solución | Estado | Validado Por |
|-------|--------|---------|----------|----------|--------|--------------|
| 2026-05-07 | AUTOFILL-FIX | `pqrs_manager.py` | Formularios vacíos tras mensaje inicial | Implementada extracción heurística con regex | ✅ | Gemini CLI |
| 2026-05-07 | PDF-LAYOUT-FIX | `pdf_service.py`, `*.j2` | Overlap QR, desorden y leyes vacías | Implementado base_layout.j2 y sanitización | ✅ | Gemini CLI |

## Detalle de Reparaciones

### 2026-05-07 - AUTOFILL-FIX
**Archivo**: `app/services/pqrs_manager.py`
**Problema**: El sistema no aprovechaba la información proporcionada por el usuario en el primer mensaje (nombre, cédula, ciudad, dirección), obligándolo a rellenar manualmente datos ya entregados.
**Solución**: Se implementó `_extract_user_data_from_message` usando regex para capturar estas entidades antes de la orquestación legal. Se dio prioridad a la extracción del usuario sobre los resultados del agente para mejorar la UX.

### 2026-05-07 - PDF-LAYOUT-FIX
**Archivos**: `app/services/pdf_service.py`, `templates/pdf/*.j2`
**Problema**: 
1. El código QR se solapaba con el texto.
2. Las leyes no se renderizaban correctamente (bucle de caracteres).
3. Los documentos carecían de una estructura visual profesional.
4. Nombres con errores tipográficos de OCR (ej: "Edurado").

**Solución Aplicada**:
1. Se creó `base_layout.j2` con CSS rígido y posicionamiento absoluto seguro para el QR.
2. Se implementó `clean_citations_list` en Python para filtrar basura antes de renderizar.
3. Se agregaron filtros de sanitización para nombres y apellidos.
4. Se migraron los templates principales (`proyeccion`, `memorial`, `traslado`) para extender el nuevo layout base.

**Validación**:
```bash
# Reiniciar worker. Finalizar trámite.
# Verificar que el PDF tiene márgenes de 2.5cm y el QR está en la esquina superior derecha limpia.
```

---

### 2026-05-07 - BUG-WIN-LOOP
**Archivo**: `app/tasks/pqrsd_tasks.py`, `main.py`
**Problema**: Error `NotImplementedError` al generar PDFs en Windows con Playwright.
**Root Cause**: El loop por defecto en Windows hilos no soporta subprocesos.
**Solución**: Se forzó la política `WindowsProactorEventLoopPolicy` globalmente.

### 2026-05-07 - BUG-PDF-001
**Archivo**: `app/services/pdf_service.py`
**Problema**: Bucle infinito en el template Jinja por recibir `citas_verificables` como string.
**Solución**: Parseo explícito con `json.loads` y fallback de lista.

### 2026-05-07 - BUG-PDF-002
**Archivo**: `app/services/pdf_service.py`
**Problema**: Fechas y números de resolución aparecían como "POR DEFINIR".
**Solución**: Inyección dinámica de `fecha_actual` y generador de `numero_resolucion`.

---

### 2026-05-07 - PQRS-PDF-FIX
**Archivo**: `app/services/pqrs_manager.py`
**Problema**: 
La generación de PDFs fallaba porque `finalize_pqrs` no recuperaba correctamente los datos de Redis (debido a la serialización de bytes) y faltaba el mapeo de variables críticas como `analisis_ia` y el radicado correcto.

**Root Cause**: 
Redis retorna diccionarios con llaves en `bytes` si no se normalizan. Al fallar el acceso a `state.get("radicado")`, se usaba un fallback que no coincidía con el esperado por el sistema de persistencia, y la falta de datos causaba que `pdf_service` retornara un paquete vacío.

**Solución Aplicada**:
1. Se normalizaron las llaves y valores de Redis (bytes a str).
2. Se aseguró la recuperación del radicado real de la sesión.
3. Se agregaron fallbacks para `borrador_proyeccion` y `analisis_ia` para evitar documentos vacíos.

**Validación**:
```bash
# Ejecutar flujo hasta fase 4 y confirmar. Verificar creación de archivos en /vault_digital/
```

---

### 2026-05-07 - PQRS-POLLING-FIX
---

### 2026-05-07 - PQRS-INIT
**Archivo**: `app/services/pqrs_manager.py`
**Problema**: Falta método `register_citizen_consent`.
**Solución**: Implementación completa del método con persistencia SQL/Redis/Ledger.
