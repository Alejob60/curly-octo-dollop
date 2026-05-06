# 🚀 Directrices del Proyecto - Orbital Prime (Diamond Edition V64.2)

## 📋 Gestión de Progreso
- El progreso se rastrea exclusivamente en `PLAN_MAESTRO.md`.
- Cualquier cambio en la arquitectura o hitos debe reflejarse en dicho archivo.

## 🛠️ Estándares Técnicos (Diamond V64.2)
- **IA:** Gemini 2.5 Flash para auditoría forense; Vertex AI con Failover Regional para RAG.
- **Seguridad:** Cumplimiento estricto Ley 1581. Rehidratación nuclear de PII solo en generación final.
- **Estabilidad Backend:**
    - **PhaseGuard:** Uso obligatorio de transiciones atómicas.
    - **Redis:** `decode_responses=True` es global. PROHIBIDO usar `.decode()` en variables de estado.
    - **PDF Engine:** En Windows, usar el puente `sync_playwright` con `ThreadPoolExecutor` para evitar `NotImplementedError`.
    - **Bóveda Digital:** Carpeta única por radicado (`vault_digital/RAD-XXXX/`). Rutas relativas forzadas con forward slashes (`/`) para compatibilidad web.
- **Estabilidad Frontend:**
    - **Sesión Inmortal:** Persistencia obligatoria en `sessionStorage` (mensajes, contador, isProcessing).
    - **Polling de Progreso:** Intervalo de 2s para sincronizar `ProcessingCard` con el backend.
    - **Overlay de Distracción:** Bloqueo de UI (Z-Index 50) durante la generación para proteger el estado del chat.

## 🤖 Protocolo de Sub-Agentes (Skills)
- **Orden de Trabajo:** Antes de modificar lógica de flujo, verificar la fase actual en `app/services/phase_orchestrator.py`.
- **Validación E2E:** Cada cambio en el backend debe verificarse con `scripts/test_backend_e2e.py`.
- **Consistencia:** Mantener la etiqueta `DIAMOND_V64_STABLE` en el header para auditoría de caché.

## 📂 Estructura de Documentación
- `PRODUCT_DOCUMENTATION/`: Informes técnicos y manuales operativos.
- `PLAN_MAESTRO.md`: Registro de tareas y estado actual del Sprint.
