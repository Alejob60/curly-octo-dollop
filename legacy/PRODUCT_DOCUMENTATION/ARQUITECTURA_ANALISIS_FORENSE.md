# 🏛️ Informe de Arquitectura: Inteligencia de Análisis y Ciclo de Vida PQRSD
**Versión:** 48.17 (Diamond Grade)  
**Sistema:** Orbital Prime Cali  

## 1. El Cerebro de Análisis (Vertex AI + RAG)

El análisis de una solicitud no es una simple lectura de texto; es un proceso de **Ingeniería Forense** que se divide en 3 capas críticas:

### A. El Túnel de Privacidad (Capa 1: Protección)
Antes de que la Inteligencia Artificial (Gemini 2.5 Flash) vea el mensaje, el `PrivacyShieldService` intercepta la entrada:
1.  **Detección de PII:** Identifica Cédulas, Nombres, Teléfonos y Direcciones.
2.  **Tokenización:** Guarda los datos reales en **PostgreSQL** (`session_tokens`) y los reemplaza en el texto por etiquetas como `[ID_1]`, `[NAME_1]`.
3.  **Inferencia Ciega:** La IA procesa el caso **sin conocer la identidad real**, cumpliendo al 100% con la **Ley 1581 (Habeas Data)**.

### B. El Motor de Grounding (Capa 2: MongoDB Atlas)
¿Cómo sabe el sistema qué leyes aplicar? El `LegalCitationEngine` realiza una búsqueda semántica:
1.  **Tagging Dinámico:** El sistema escanea palabras clave en la solicitud (ej: "EPS" -> salud, "pavimento" -> malla_vial).
2.  **Consulta a MongoDB:** Busca en la colección `normativa_colombia` los artículos vigentes.
3.  **Inyección de Contexto:** Los textos literales de las leyes (Ley 1755, CPACA, Ley 100) se inyectan en el prompt de la IA como "Verdad Absoluta".

### C. Extracción Estructurada (Capa 3: One-Shot Analysis)
La IA genera un JSON que contiene:
*   **Dependencia Competente:** Basado en la estructura orgánica de la Alcaldía.
*   **Soporte de Traslado:** Justificación jurídica de por qué esa oficina debe atender el caso.
*   **Borrador de Respuesta:** Propuesta de resolución de fondo.
*   **Etiquetas Legales:** Identificadores para el motor de PDF.

---

## 2. Persistencia y Sincronización de Datos

El sistema utiliza un modelo de **Persistencia Dual** para garantizar que nada se pierda:

1.  **PostgreSQL (Búnker Ciudadano):**
    *   Se utiliza para el `UserProfileService`. 
    *   Tan pronto como se confirma una identidad, los datos se guardan físicamente en la tabla de ciudadanos.
    *   Sirve como "Ancla de Verdad" para futuras solicitudes del mismo usuario.
2.  **Valkey / Redis (Memoria de Estado):**
    *   Gestiona el `PhaseGuard` (Máquina de Estados).
    *   Guarda los "Slots" (huecos de información) de la sesión actual.
    *   Evita los bucles: si una fase está marcada como completada en Redis, el sistema nunca vuelve atrás.

---

## 3. Generación de la Trilogía Documental

Cuando el ciudadano firma (`handleFinalize`), el sistema activa el `PDFService`:

1.  **Rehidratación:** El sistema recupera los datos reales de PostgreSQL y reemplaza los tokens `[ID_1]` en los textos redactados por la IA.
2.  **Ensamble de PDFs:**
    *   **Memorial:** Inyecta las citas de la Ley 1755 obtenidas de MongoDB.
    *   **Traslado:** Usa la redacción técnica de la IA para justificar la competencia.
    *   **Proyección:** Incluye la propuesta de solución de fondo.
3.  **Sello QR y Ledger:**
    *   Genera un QR único vinculado a la URL de validación.
    *   Crea un Hash SHA-256 de los documentos y lo firma en el **AuditLedger** de PostgreSQL.

---

## 4. Operaciones de Validación (¿Cómo sabemos que está bien?)

Para garantizar la excelencia, el sistema realiza 4 validaciones automáticas:

1.  **Validación de Esquema (json-repair):** Si la IA devuelve un JSON malformado, el sistema lo repara automáticamente o aplica un regex de emergencia para extraer los campos clave.
2.  **Validación de PhaseGuard:** Antes de avanzar de fase (F2 -> F3), el sistema verifica que los campos obligatorios (`documento`, `email`, `direccion`) estén presentes en Redis. Si no, bloquea la transición.
3.  **Check de Grounding:** El sistema solo inyecta leyes que estén marcadas como `vigente: True` en MongoDB.
4.  **Integridad de Sello:** El sello QR contiene el Hash del documento. Si el PDF es alterado, el QR dejará de ser válido al ser escaneado por el funcionario.

---
*Informe Técnico producido por el Orquestador Orbital Prime V48.17.*
