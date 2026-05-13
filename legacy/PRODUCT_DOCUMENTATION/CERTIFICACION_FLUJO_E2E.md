# 🛡️ Certificación de Flujo Forense: Orbital Prime V48

Este informe técnico detalla el cumplimiento del ciclo de vida de una PQRSD, mapeando cada fase con sus servicios y archivos responsables.

---

## 🟢 FASE 1: Ingesta, Escudo de Privacidad y Slot Filling
**Objetivo:** Capturar la solicitud, proteger datos sensibles y determinar vacíos de información.

| Sub-paso | Servicio / Archivo | Acción Técnica |
| :--- | :--- | :--- |
| **Captura Inicial** | `CaliLexPrime.jsx` (Frontend) | Envía el mensaje masivo al endpoint `/analyze`. |
| **Detección PII** | `privacy_shield_service.py` | Detecta nombres y cédulas usando Regex/DLP. |
| **Bóveda Identidad** | `sql_models.py` (PostgreSQL) | Guarda datos reales en `citizen_vault`. |
| **Anonimización** | `pqrs_manager.py` | Reemplaza datos reales por tokens `[ID_1]`, `[NOMBRE_1]`. |
| **Extracción IA** | `vertex_client.py` (Gemini 2.5) | Extrae el JSON de slots (Asunto, Ubicación, Vacíos). |
| **Lógica UI** | `pqrs_manager.py` | Decide qué `Card` (Identidad/Contacto) mostrar. |

---

## 🟡 FASE 2: Triaje y Grounding Jurídico (RAG)
**Objetivo:** Clasificar dependencias y blindar el caso con leyes reales.

| Sub-paso | Servicio / Archivo | Acción Técnica |
| :--- | :--- | :--- |
| **Consulta RAG** | `legal_citation_engine.py` | Busca leyes en **MongoDB Atlas** basadas en el asunto. |
| **Clasificación** | `use_case_service.py` | Determina que el caso va a **Infraestructura** y **Movilidad**. |
| **PhaseGuard** | `phase_orchestrator.py` | Bloquea retrocesos; el sistema "sabe" que ya pasó Identidad. |
| **Status Log** | `pqrs_manager.py` (Postgres) | Registra el evento `IA_EXTRACTION_SUCCESS` en el Ledger local. |

---

## 🔵 FASE 3: Rehidratación y Trilogía Documental
**Objetivo:** Transformar tokens en documentos legales reales.

| Sub-paso | Servicio / Archivo | Acción Técnica |
| :--- | :--- | :--- |
| **Rehidratación** | `privacy_shield_service.py` | Cruza tokens con PostgreSQL para recuperar datos reales. |
| **Búnker GCS** | `vault_manager.py` | Crea la estructura de carpetas `01_Peticion`, `02_Proyeccion`. |
| **Generación PDF** | `pdf_service.py` | Crea Memorial, Oficio de Traslado y Borrador Jurídico. |
| **Sello QR** | `pdf_service.py` | Genera e inyecta el QR de validación en tiempo real. |

---

## 🟣 FASE 4: Notificación y Sellado Inmutable
**Objetivo:** Garantizar la entrega y la inalterabilidad legal (Ley 1437).

| Sub-paso | Servicio / Archivo | Acción Técnica |
| :--- | :--- | :--- |
| **Sello WORM** | `gcp_storage_service.py` | Activa la política de retención de 20 años en el objeto. |
| **Firma KMS** | `signer.py` | Firma el Hash del documento con llaves HSM de Google Cloud. |
| **Notificación** | `notification_service.py` | Envía email vía **GCP SMTP Relay** con la trilogía adjunta. |
| **Finalización** | `pqrs.py` | Limpia tokens temporales de PostgreSQL tras éxito total. |

---

## 🔴 FASE 5: Gobernanza y Resolución (Dashboard)
**Objetivo:** Proveer herramientas de gestión al funcionario.

| Sub-paso | Servicio / Archivo | Acción Técnica |
| :--- | :--- | :--- |
| **Visualización** | `GovernanceDashboard.jsx` | Muestra la carga de trabajo por dependencia. |
| **Tracking** | `pqrs.py` (GET /track) | Permite al ciudadano consultar el estado con su QR/CC. |
| **Trazabilidad** | `ledger_service.py` | Expone la cadena de custodia de cada radicado. |

---
*Certificación generada para Orbital Prime GovDocs Ecosystem · 2026*
