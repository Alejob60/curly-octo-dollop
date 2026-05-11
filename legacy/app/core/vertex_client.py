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
    """
    def __init__(self):
        self.regions = ["us-central1", "us-east4", "us-west1", "europe-west1", "asia-northeast1"]
        self.current_region_index = 0
        self.model_name = settings.VERTEX_MODEL_NAME
        self._init_client()

    def _init_client(self):
        region = self.regions[self.current_region_index]
        try:
            self.client = genai.Client(
                vertexai=True,
                project=settings.GCP_PROJECT_ID,
                location=region,
                http_options=types.HttpOptions(api_version="v1")
            )
            logger.info(f"🚀 [GCP NATIVE V34.3] Vertex AI Activado en {region} (Silent Mode)")
        except Exception as e:
            logger.error(f"❌ Error al inicializar Cliente en {region}: {e}")
            self.client = None

    def _rotate_region(self):
        self.current_region_index = (self.current_region_index + 1) % len(self.regions)
        new_region = self.regions[self.current_region_index]
        logger.warning(f"🔄 [FAILOVER] Rotando a región: {new_region}")
        self._init_client()

    async def generate_content(self, contents: list, generation_config: dict = None, system_instruction: str = None) -> str:
        if not self.client:
            self._init_client()
            if not self.client: return "[FALLO_IA_CLIENTE_NO_DISPONIBLE]"

        try:
            si = system_instruction or SYSTEM_INSTRUCTION
            config = types.GenerateContentConfig(
                system_instruction=si,
                temperature=0.1,
                response_mime_type="application/json"
            )

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
            # Usamos el modelo configurado o el default 004
            model = getattr(settings, "AI_EMBEDDING_MODEL", "text-embedding-004")
            response = self.client.models.embed_content(
                model=model,
                contents=[text[:2000]] # Límite de seguridad
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"⚠️ Error generando embedding: {e}")
            return [0.0] * 768

vertex_client = VertexGCPClientV34()
