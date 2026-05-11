# 🏛️ ARQUITECTURA TOTAL: ORBITAL PRIME (DIAMOND V64.2)

Este documento contiene el mapeo exhaustivo de todos los servicios, su interacción con el frontend y el flujo de datos bajo el monitoreo **Ojo de Dios**.

## 📂 1. Árbol de Proyecto y Mapa de Servicios

```text
orbital-prime-govdocs-engine/
├── app/
│   ├── api/v1/
│   │   └── pqrs.py              # 🚪 Puerta de enlace. Gestiona estados y polling.
│   ├── core/
│   │   ├── vertex_client.py     # ☁️ Conector regional con Vertex AI.
│   │   ├── db_clients.py        # 🗄️ Gestión de Valkey, Postgres y Mongo.
│   │   └── case_registry.yaml   # 📂 Diccionario maestro de perfiles y leyes.
│   ├── services/
│   │   ├── pqrs_manager.py      # 🧠 Orquestador de Flujo y Smart Extraction.
│   │   ├── pdf_service.py       # 📄 Generador de PDFs (Anti-Artefactos).
│   │   ├── phase_orchestrator.py # 🛡️ PhaseGuard: Bloqueo de estados inválidos.
│   │   ├── persistence_bridge.py # 💾 Sincronizador SQL (PostgreSQL).
│   │   ├── legal_agents/        # ⚖️ Inteligencia Colectiva (Multi-Agente)
│   │   │   ├── orchestrator.py  # 🔄 Recursive Audit Loop.
│   │   │   ├── extractor.py     # 🔍 Identifica hechos y peticionario.
│   │   │   ├── researcher.py    # 📚 RAG: Busca leyes aplicables.
│   │   │   ├── crafter.py       # ✍️ Redacta borradores jurídicos.
│   │   │   └── reviewer.py      # ⚖️ Auditor de calidad y peso legal.
│   │   ├── privacy_shield_service.py # 🛡️ Tokenizador PII (Ley 1581).
│   │   ├── ledger_service.py    # ⛓️ Registro inmutable en GCP.
│   │   ├── crypto_service.py    # 🔐 Cifrado nuclear de datos sensibles.
│   │   ├── autonomous_routing.py # 🗺️ Enrutamiento IA por competencia.
│   │   ├── judicial_engine_service.py # ⚖️ Motor de lógica judicial avanzada.
│   │   ├── master_data_service.py # 🏛️ Gestión de dependencias y funcionarios.
│   │   ├── notification_service.py # 📧 Alertas vía Email/GCP-Relay.
│   │   ├── qr_service.py        # 📱 Generador de códigos de verificación.
│   │   ├── rag_service.py       # 📚 Motor de recuperación normativa.
│   │   ├── sla_monitor.py       # ⏱️ Vigilante de términos legales.
│   │   ├── telemetry_agent.py   # 📊 Monitor de performance y costos IA.
│   │   ├── websocket_manager.py # 🔌 Comunicación tiempo real Frontend.
│   │   └── audit_service.py     # 🔍 Trazabilidad de acciones de usuario.
│   └── tasks/
│       └── pqrsd_tasks.py       # ⚙️ Worker Celery (Windows Proactor).
└── templates/pdf/
    ├── base_layout.j2           # 🖼️ Layout visual con QR seguro.
    ├── proyeccion.j2            # ⚖️ Borrador de Resolución.
    └── memorial.j2              # 📜 Requerimiento Ciudadano.
```

## 🧠 2. ¿Por qué hay tantos servicios? (Mapeo de Funcionalidades)

Muchos de estos servicios son **capas de soporte infraestructural** que aseguran que el motor sea de grado gubernamental:

*   **Seguridad y Privacidad**: `privacy_shield_service`, `crypto_service` e `integration_security_service` aseguran que ningún dato de salud o cédula viaje en texto plano por la nube.
*   **Cumplimiento Legal**: `sla_monitor` y `compliance_monitor` calculan los días de vencimiento y aseguran que los documentos sigan la Ley 1437.
*   **Auditabilidad**: `ledger_service` y `audit_service` crean el sello inmutable. Si un documento se genera hoy, nadie (ni siquiera el admin) puede decir que se generó ayer.
*   **Inteligencia de Negocio**: `analytics_service` y `metrics_service` reportan cuántas PQRS se resuelven por día y qué tan eficiente es cada Secretaría.
*   **Autogestión**: `auto_repair_service` detecta si un PDF salió mal y reintenta la generación automáticamente antes de que el usuario lo note.

## 🔄 3. Diagrama de Flujo: Frontend ↔ Backend (State Loop)

```text
[ CIUDADANO (React + Vite) ]        [ ORQUESTADOR (FastAPI) ]        [ CEREBRO (Multi-Agente IA) ]
           |                                   |                                |
    (1) Primer Mensaje ----------------> (2) Analyze PQRS                       |
           |                          (Extract Basic Info)                      |
           | <--- Retorna IdentityCard <-------|                                |
           |      (Autofill con Regex)         |---(3) BackgroundTask ----------|
           |                                   |      (Orquestación Legal)      |
           |                                   |               |                |
           |                                   |      [ EXTRACTOR ] -> Hechos   |
           |                                   |      [ RESEARCHER] -> Leyes    |
    (4) Usuario revisa/edita                   |      [ CRAFTER   ] -> Borrador |
           |                                   |      [ REVIEWER  ] -> Auditoría|
    (5) Update-Slot (Fases) -----------> (6) Persiste en DB <----------|        |
           |                          (Actualiza Redis)                         |
           |                                   |                                |
    (7) Polling de Progreso <----------> (8) Consulta Redis                     |
           |                                   |                                |
    (9) Confirmación Final -----------> (10) Encola en Celery ----------------> (11) Finalize
           |                           (ProcessingCard)                         |
           |                                   |                         (Generación PDF)
           |                                   |                         (Sello Inmutable)
           | <--- Retorna SuccessCard <--------|                         (Subida a Vault)
           |      (Links de descarga)          | <------------------------------|
```

## 🏗️ 4. Diagrama de Servicio: El Ciclo de Auditoría IA

```text
       [ ENTRADA ]
           |
    [ EXTRACTOR NER ] -----> [ RESEARCHER RAG ]
           |                       |
           +-----> [ CRAFTER ] <---+
                      ^ |
                      | v
               [ REVIEWER AGENT ]
               (Score < 0.8 ?) --- SI ---+
                      |                  |
                      NO                 |
                      |          (Feedback Recursivo)
                      v                  |
               [ JSON APROBADO ] <-------+
```

---

**NOTA FINAL**: El sistema está diseñado para que cada componente sea intercambiable. Si cambiamos de Vertex AI a un modelo local, solo se toca `vertex_client.py`, el resto del flujo **Ojo de Dios** permanece intacto. 🚀⚖️💎⚡
