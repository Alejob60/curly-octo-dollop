import os
from openai import AsyncOpenAI
from loguru import logger
from app.core.config import settings

class NvidiaNIMClient:
    """
    CLIENTE V55.5: Integración con NVIDIA NIMs (Inference Microservices).
    Proporciona inferencia de alta velocidad para validación y auditoría forense.
    """
    def __init__(self):
        self.api_key = settings.NVIDIA_NIMS_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.model_name = "meta/llama-3.1-70b-instruct" # Modelo por defecto para NIM
        
        if not self.api_key:
            logger.warning("⚠️ NVIDIA_NIMS_API_KEY no detectada. NvidiaNIMClient operará en modo limitado.")
            self.client = None
        else:
            try:
                self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
                logger.info(f"🚀 [NVIDIA NIM V55.5] Cliente Activado (Model: {self.model_name})")
            except Exception as e:
                logger.error(f"❌ Error al inicializar NvidiaNIMClient: {e}")
                self.client = None

    async def generate_content(self, prompt: str, system_instruction: str = None) -> str:
        if not self.client:
            return "[FALLO_IA_NVIDIA_UNAVAILABLE]"
        
        try:
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            completion = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.2,
                top_p=0.7,
                max_tokens=2048,
                stream=False
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ Error en Nvidia NIM Generation: {e}")
            return f"[FALLO_IA_NVIDIA_ERROR: {str(e)}]"

nvidia_nim_client = NvidiaNIMClient()
