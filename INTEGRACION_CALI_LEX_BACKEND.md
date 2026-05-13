# ⚖️ Manual de Integración Técnica: Cali-Lex Advisor (V65.5)

Este documento detalla el procedimiento para integrar el agente **Cali-Lex Advisor** con el backend de **GovDocs**. El sistema está diseñado bajo una arquitectura de "Motor Determinista", donde el agente entrega estructuras JSON validadas que el backend convierte en folios oficiales.

---

## 🏗️ 1. Arquitectura de Integración

La integración se basa en un flujo de tres capas:

1.  **Capa de Inteligencia (Vertex AI ADK):** Procesa el texto crudo y genera el JSON estricto de 5 documentos.
2.  **Capa de Orquestación (Backend V2):** Valida la confianza del agente y gestiona las colas de trabajo.
3.  **Capa de Renderizado (PDF Service):** Toma el JSON validado y lo inyecta en plantillas Jinja2/WeasyPrint.

---

## ⚙️ 2. Variables de Entorno (GCP & Backend)

Configura estas variables en tu archivo `.env` o en los Secretos de Cloud Run:

```env
# Identificadores de GCP
CALI_LEX_PROJECT_ID=misybot-ai-beta
CALI_LEX_LOCATION=us-central1
CALI_LEX_ENGINE_ID=2046231271465549824

# Configuración de API
CALI_LEX_URL=https://us-central1-aiplatform.googleapis.com/v1/projects/misybot-ai-beta/locations/us-central1/reasoningEngines/2046231271465549824:streamQuery

# Umbrales de Seguridad
MIN_CONFIDENCE_THRESHOLD=0.85
MAX_PQRS_WORKERS=4
APP_VERSION=V65.5
```

---

## 📡 3. Contrato de API (Input / Output)

### A. Petición (Request)
El backend debe enviar un payload JSON con la información mínima del ciudadano:

```json
{
  "input": {
    "message": "Solicito información sobre mi radicado 2024-001 y el estado de mi multa de tránsito."
  }
}
```

### B. Respuesta (Response JSON)
El agente devolverá un objeto con la estructura `StrictLegalOutput`. El backend debe mapear los siguientes bloques críticos:

*   **`decision_recommendation`**: Determina si se aprueba, deniega o requiere más info.
*   **`flujo_documentos`**: Contiene el texto para los 5 archivos (traslado, proyección, logística, memorial, auto).
*   **`auditoria.confidence_score`**: Debe ser `>= 0.85` para permitir la generación automática.

---

## 👷 4. Procesamiento de Cola (Batch Worker)

Para procesar los registros históricos (46k), el backend utiliza un worker asíncrono con semáforo para evitar saturación de cuota.

**Flujo del Worker:**
1.  Lee registro de MongoDB (`status: PENDING`).
2.  Llama al agente Cali-Lex.
3.  **Valida Confianza:**
    *   Si score `< 0.85` ➡️ Mueve a `pqrs_human_review`.
    *   Si score `≥ 0.85` ➡️ Guarda JSON y dispara generador de PDF.
4.  Marca como `COMPLETED`.

---

## 📄 5. Generación de Documentos (PDF)

El backend utiliza el servicio `pdf_generator.py` para renderizar los folios. 

**Reglas de Renderizado:**
*   **Anti-Alucinación:** Si el campo `peticionario.nombres` es `null`, el template debe mostrar "PENDIENTE VERIFICACIÓN".
*   **Marca de Agua:** El hash SHA-256 del bloque `watermark` debe ir impreso en el pie de página.
*   **Alerta de Fecha:** Si `fecha_valida` es `false`, se debe inyectar el bloque de advertencia en el encabezado.

---

## 🛡️ 6. Protocolo de Errores

| Código de Error | Causa | Acción Recomendada |
| :--- | :--- | :--- |
| `FAILED_PRECONDITION` | Sincronización de GCP | Esperar 2-5 min; el motor se está activando. |
| `CONFIDENCE_LOW` | Datos ambiguos o insuficientes | Enviar a revisión manual del área jurídica. |
| `INVALID_REQUEST` | Payload mal formado | Verificar que el input sea un objeto `{"input": {"message": "..."}}`. |

---

## 🚀 7. Comandos de Inicio Rápido

```bash
# 1. Cargar normativa técnica a MongoDB
python seed_legal_knowledge.py

# 2. Migrar registros legacy a la cola
python migrate_legacy_batch.py

# 3. Iniciar procesamiento automático
python production_worker.py
```

---
**Manual de Integración V65.5**  
*Certificado por: Cali-Lex Agent Core Team*
