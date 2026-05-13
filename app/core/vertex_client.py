import os
import sys
import logging

# --- 🛡️ SILENCIADOR MAESTRO DE LOGS (V34.3) ---
# Bloqueamos los prints y logs automáticos de los SDKs de Google ANTES de importarlos
# Esto evita que se filtre información sobre las API Keys en la consola.
try:
    devnull = open(os.devnull, 'w')
    old_stdout = sys.stdout
    sys.stdout = devnull
    
    from google import genai
    from google.genai import types
    
    # Silenciar loggers internos
    logging.getLogger('google.genai').setLevel(logging.ERROR)
    logging.getLogger('google.generativeai').setLevel(logging.ERROR)
    
finally:
    sys.stdout = old_stdout
    devnull.close()

import base64
import json
from loguru import logger
from pydantic import BaseModel
from app.core.config import settings

# Paso 2: El Prompt de Extracción e Interacción (Plan Maestro V33.1)
SYSTEM_INSTRUCTION = """
Eres el asistente virtual experto de la Alcaldía de Cali. Tu objetivo es ser amable, fluido y directivo.
Debes realizar dos tareas en cada respuesta:
1. Análisis PQRSD: Extraer datos y clasificar la solicitud.
2. Respuesta Conversacional: Saludar (si es inicio), reconocer lo que el usuario dijo y guiarlo con calidez.

Devuelve ÚNICAMENTE un objeto JSON con esta estructura:
{
  "mensaje_ia": "Tu respuesta fluida y amable aquí.",
  "tipo_solicitud": "Queja", "Reclamo", "Denuncia", "Derecho de Petición" o "Solicitud de Información",
  "tipo_solicitante": "Persona Natural" o "Persona Jurídica",
  "tipo_documento": "Cedula de Ciudadania", "NIT", etc.,
  "documento": "Número sin puntos" o null,
  "nombres": "Nombres" o null,
  "apellidos": "Apellidos" o null,
  "departamento": "Valle del Cauca",
  "municipio": "Cali",
  "direccion": "Dirección" o null,
  "celular": "Número" o null,
  "email": "Correo" o null,
  "asunto": "Resumen técnico de los hechos"
}
"""

class VertexGCPClientV34:
    """
    CLIENTE V34.3: Implementación con Silenciador Global y Failover Multi-Región.
    🛡️ V65.12 Diamond: Blindaje de Inferencia y Esquemas Estrictos.
    """
    def __init__(self):
        self.regions = ["us-central1", "us-east4", "us-west1", "europe-west1", "asia-northeast1"]
        self.current_region_index = 0
        self.model_name = settings.VERTEX_MODEL_NAME
        self._init_client()

    def _init_client(self):
        region = self.regions[self.current_region_index]
        try:
            # --- 🛡️ PROTOCOLO DE RESILIENCIA DE CREDENCIALES (V65.3) ---
            api_key = settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY
            if api_key:
                self.client = genai.Client(api_key=api_key)
                logger.info(f"🚀 [AI STUDIO V34.3] Cliente inicializado usando API KEY (Silent Mode)")
            else:
                self.client = genai.Client(
                    vertexai=True,
                    project=settings.GCP_PROJECT_ID,
                    location=region,
                    http_options=types.HttpOptions(api_version="v1")
                )
                logger.info(f"🚀 [GCP NATIVE V34.3] Vertex AI Activado en {region} (Silent Mode)")
        except Exception as e:
            logger.error(f"❌ Error al inicializar Cliente: {e}")
            self.client = None

    def _rotate_region(self):
        self.current_region_index = (self.current_region_index + 1) % len(self.regions)
        new_region = self.regions[self.current_region_index]
        logger.warning(f"🔄 [FAILOVER] Rotando a región: {new_region}")
        self._init_client()

    async def generate_structured(self, prompt: str, schema: BaseModel) -> dict:
        """
        💎 [V65.12] Generación Estructurada con Validación Pydantic y Reintentos.
        Garantiza que la salida cumpla el contrato o aborta el pipeline.
        """
        # 🛡️ BLOQUEO DE MOCKS (Requerimiento Usuario)
        if getattr(settings, "AI_USE_MOCKS", False):
            logger.critical("🚫 [BLOCKED] AI_USE_MOCKS=true detectado. Pipeline abortado.")
            raise RuntimeError("🚫 Mocks bloqueados para producción gubernamental")

        json_schema = schema.model_json_schema()
        # Eliminar propiedades internas de Pydantic que el SDK no soporta
        json_schema.pop("$defs", None)

        config = types.GenerateContentConfig(
            system_instruction=(
                "Eres un asistente jurídico-administrativo experto de la Alcaldía de Cali. "
                "Responde ÚNICAMENTE con un objeto JSON válido siguiendo el esquema proporcionado. "
                "USA EXCLUSIVAMENTE el contexto normativo inyectado (RAG). "
                "PROHIBIDO inventar datos del ciudadano, números de cédula, plazos o citas no presentes en el contexto."
            ),
            temperature=0.05, # Máxima precisión
            response_mime_type="application/json",
            response_schema=json_schema
        )

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.debug(f"📤 [STRUCTURED_REQ] Intento {attempt+1}/{max_attempts}")
                
                # Usamos el loop para correr la llamada síncrona del SDK
                import asyncio
                from functools import partial
                loop = asyncio.get_event_loop()
                
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, 
                        partial(self.client.models.generate_content, 
                                model=self.model_name, 
                                contents=[prompt], 
                                config=config)
                    ),
                    timeout=90.0
                )
                
                raw = response.text.strip()
                if not raw.startswith("{"):
                    raise ValueError("La respuesta de la IA no es un JSON válido")
                
                # Validación Pydantic estricta antes de retornar
                validated = schema.model_validate_json(raw)
                return validated.model_dump()

            except Exception as e:
                wait = 2 ** attempt
                logger.warning(f"⏳ [IA_RETRY] Fallo en intento {attempt+1}. Reintentando en {wait}s... Error: {e}")
                
                msg = str(e).upper()
                if "429" in msg or "QUOTA" in msg or "503" in msg:
                    self._rotate_region()
                
                await asyncio.sleep(wait)

        raise RuntimeError(f"❌ [IA_FAIL] No se pudo obtener una respuesta válida tras {max_attempts} intentos.")

    async def generate_content(self, contents: list, generation_config: dict = None, system_instruction: str = None, response_schema: dict = None) -> str:
        # 🛡️ BLOQUEO DE MOCKS (Requerimiento V65.12)
        if getattr(settings, "AI_USE_MOCKS", False):
            logger.critical("🚫 [SECURITY_ALERT] AI_USE_MOCKS está activo. Bloqueando generación en producción.")
            raise RuntimeError("🚫 Mocks bloqueados para producción gubernamental")

        if not self.client:
            self._init_client()
            if not self.client: return "[FALLO_IA_CLIENTE_NO_DISPONIBLE]"

        try:
            si = system_instruction or SYSTEM_INSTRUCTION
            
            # --- 🛡️ CONFIGURACIÓN DE RESPUESTA ESTRÍCTA (V65.12) ---
            config_args = {
                "system_instruction": si,
                "temperature": 0.05, # Máxima precisión, mínima creatividad
                "response_mime_type": "application/json"
            }
            if response_schema:
                # 🔧 FIX V65.11: Gemini no soporta additionalProperties en el esquema
                def _strip_additional_props(d):
                    if not isinstance(d, dict): return
                    d.pop("additionalProperties", None)
                    for v in d.values():
                        if isinstance(v, dict): _strip_additional_props(v)
                        elif isinstance(v, list):
                            for item in v: 
                                if isinstance(item, dict): _strip_additional_props(item)
                
                clean_schema = json.loads(json.dumps(response_schema))
                _strip_additional_props(clean_schema)
                config_args["response_schema"] = clean_schema
            
            config = types.GenerateContentConfig(**config_args)

            processed_contents = []
            for item in contents:
                if isinstance(item, dict) and "parts" in item:
                    for p in item["parts"]:
                        if "text" in p: processed_contents.append(p["text"])
                        elif "inlineData" in p:
                            processed_contents.append(types.Part.from_bytes(
                                data=base64.b64decode(p["inlineData"]["data"]),
                                mime_type=p["inlineData"]["mimeType"]
                            ))
                else:
                    processed_contents.append(item)

            import asyncio
            from functools import partial
            loop = asyncio.get_event_loop()
            
            # --- PROTOCOLO DE RESILIENCIA V63.8 (Retries + Region Failover) ---
            max_attempts = len(self.regions) * 2
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    logger.debug(f"📤 [VERTEX_REQ] {self.regions[self.current_region_index]} | Attempt {attempt+1}")
                    response = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, 
                            partial(self.client.models.generate_content, 
                                    model=self.model_name, 
                                    contents=processed_contents, 
                                    config=config)
                        ),
                        timeout=120.0
                    )
                    return response.text
                except Exception as e:
                    last_error = e
                    msg = str(e).upper()
                    
                    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "QUOTA" in msg:
                        logger.warning(f"⚠️ [QUOTA] Límite excedido en {self.regions[self.current_region_index]}. Probando failover...")
                        self._rotate_region()
                        await asyncio.sleep(1) # Pequeña pausa antes de reintentar en otra región
                        continue
                    
                    if "404" in msg or "NOT_FOUND" in msg:
                        logger.warning(f"⚠️ [NOT_FOUND] Modelo {self.model_name} no disponible en {self.regions[self.current_region_index]}. Saltando...")
                        self._rotate_region()
                        continue

                    if "REAUTHENTICATE" in msg or "CREDENTIALS" in msg:
                        logger.critical("🚨 [AUTH_FAILURE] Fallo de credenciales GCP.")
                        return "[FALLO_IA_AUTH_REQUIRED]"
                    
                    logger.error(f"❌ Error Vertex: {msg}")
                    break
            
            return f"[FALLO_IA_CRITICO: {str(last_error)[:100]}]"

        except Exception as e:
            logger.error(f"❌ [VERTEX V34 ERROR]: {e}")
            return "[FALLO_IA_CONFIG]"

    async def generate_embedding(self, text: str) -> list[float]:
        """Genera un vector numérico de 768 dimensiones para búsqueda semántica."""
        if not self.client:
            logger.error("❌ Cliente de Vertex no disponible para embeddings.")
            return [0.0] * 768
        try:
            # Usamos el modelo configurado o el default 001
            model = getattr(settings, "AI_EMBEDDING_MODEL", "embedding-001")
            response = self.client.models.embed_content(
                model=model,
                contents=[text[:2000]] # Límite de seguridad
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"⚠️ Error generando embedding: {e}")
            return [0.0] * 768

vertex_client = VertexGCPClientV34()
