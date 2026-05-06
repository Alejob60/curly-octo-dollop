# 🏛️ Informe Técnico de Fases: Arquitectura Orbital Prime

Este documento detalla el "bajo el capó" de cada fase del sistema, especificando qué archivos y servicios intervienen en el procesamiento de una PQRSD.

---

## 🟢 FASE 1: Ingesta Multimodal y Escudo de Privacidad
**Propósito:** Recibir la solicitud y proteger los datos personales (Habeas Data).

1.  **Entrada de Datos:**
    *   **Archivo:** `CaliLexPrime.jsx` (Frontend) o `FormalCitizenPortal.jsx`.
    *   **Acción:** El usuario envía su historia. El frontend dispara una petición `POST` al endpoint `/analyze`.
2.  **Protección de Datos (Túnel de Privacidad):**
    *   **Servicio:** `privacy_shield_service.py` (Backend).
    *   **Acción:** El sistema detecta PII (Cédulas, Nombres, Correos) y los guarda en la tabla `session_tokens` de PostgreSQL. Reemplaza los datos por tokens (`[ID_1]`).
3.  **Registro de Auditoría:**
    *   **Archivo:** `pqrs_manager.py` -> `_log_step()`.
    *   **Acción:** Se guarda un Hash inmutable del inicio del proceso en `AuditLedger`.

---

## 🟡 FASE 2: Cerebro de Análisis, Triaje y RAG
**Propósito:** Clasificar el caso legalmente y determinar la dependencia competente.

1.  **Grounding Jurídico (RAG):**
    *   **Servicio:** `legal_citation_engine.py`.
    *   **Acción:** Consulta **MongoDB Atlas** para traer la Ley 1755 y normativas locales de Cali.
2.  **Inferencia Ciega (One-Shot):**
    *   **Servicio:** `vertex_client.py` (Gemini 2.5 Flash).
    *   **Acción:** La IA lee el texto **anonimizado**. Identifica que el caso de "Huecos" va para **Infraestructura**.
3.  **Gestión de Estado (Slot Filling):**
    *   **Archivo:** `pqrs_manager.py`.
    *   **Acción:** Compara los datos extraídos con el esquema requerido. Si falta el email, decide lanzar la `ContactCard`.
4.  **Control de Flujo (PhaseGuard):**
    *   **Servicio:** `phase_orchestrator.py`.
    *   **Acción:** Registra en **Valkey** que la Identidad fue validada y bloquea cualquier retroceso.

---

## 🔵 FASE 3: Rehidratación y Trilogía Documental
**Propósito:** Generar los soportes legales con información real.

1.  **Rehidratación Forense:**
    *   **Servicio:** `privacy_shield_service.py` -> `rehydrate_text()`.
    *   **Acción:** Justo antes de crear el PDF, el sistema recupera los nombres reales de PostgreSQL y reemplaza los tokens.
2.  **Fabricación de PDFs:**
    *   **Servicio:** `pdf_service.py`.
    *   **Acción:** Genera el **Memorial**, el **Oficio de Traslado** y el **Borrador de Respuesta**. Inyecta el **Código QR** dinámico de validación.
3.  **Búnker de Almacenamiento:**
    *   **Servicio:** `vault_manager.py`.
    *   **Acción:** Organiza los archivos en carpetas físicas inalterables: `01_Peticion_Ciudadana`, `02_Proyeccion_Dependencia`.

---

## 🟣 FASE 4: Cierre, Sello WORM y Notificación
**Propósito:** Certificar el radicado y enviarlo al ciudadano.

1.  **Sello de Integridad:**
    *   **Servicio:** `gcp_storage_service.py`.
    *   **Acción:** Aplica la política **WORM** (Write Once Read Many) de Google Cloud. El documento no puede ser borrado ni editado por 20 años.
2.  **Notificación Digital:**
    *   **Servicio:** `notification_service.py`.
    *   **Acción:** Envía el correo oficial al ciudadano vía **GCP SMTP Relay** con los 3 documentos adjuntos.
3.  **Limpieza de Seguridad:**
    *   **Archivo:** `pqrs.py` -> `/finalize`.
    *   **Acción:** Borra los tokens de PostgreSQL y la sesión de Valkey. No queda rastro de datos sensibles en la memoria volátil.

---

## 🔴 FASE 5: Gobernanza (Dashboard de Control)
**Propósito:** Gestión administrativa y trazabilidad.

1.  **Tablero de Control:**
    *   **Archivo:** `GovernanceDashboard.jsx`.
    *   **Acción:** El funcionario visualiza el radicado, el estado del SLA (15 días) y la dependencia asignada.
2.  **Verificación Externa:**
    *   **Portal Público de Validación.**
    *   **Acción:** Al escanear el QR del PDF, el sistema valida el Hash contra el Ledger de la Alcaldía.

---
*Manual Técnico de Orbital Prime V48.5 · Producido por GovTech Architect AI*
