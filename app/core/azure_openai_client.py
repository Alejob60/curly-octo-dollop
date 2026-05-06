import asyncio
import base64
from functools import lru_cache
from types import SimpleNamespace
from typing import List

import httpx
from loguru import logger
from openai import AsyncAzureOpenAI, AzureOpenAI
from vertexai import init as vertex_init
from vertexai.generative_models import GenerationConfig, GenerativeModel, Part
from vertexai.language_models import TextEmbeddingModel

from app.core.config import settings


def _validate_azure_openai_settings() -> None:
    if not settings.AZURE_OPENAI_API_KEY:
        raise RuntimeError("Missing AZURE_OPENAI_API_KEY (or AZURE_OPENAI_KEY) in environment.")
    if not settings.AZURE_OPENAI_ENDPOINT:
        raise RuntimeError(
            "Missing AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_ENDPOINT/AZURE_OPEN_API_ENDPOINT in environment."
        )


def _validate_vertex_settings() -> None:
    # Accept either API-key flow (local) or SDK flow (project/location).
    if settings.VERTEX_API_KEY:
        return
    if not settings.GCP_PROJECT_ID:
        raise RuntimeError("Missing GCP_PROJECT_ID for Vertex AI.")
    if not settings.GCP_LOCATION:
        raise RuntimeError("Missing GCP_LOCATION for Vertex AI.")


def _is_vertex_provider() -> bool:
    return settings.AI_PROVIDER == "vertex"


def _make_compat_response(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _build_vertex_payload(messages):
    text_lines = []
    parts = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if isinstance(content, str):
            text_lines.append(f"{role}: {content}")
            continue

        if isinstance(content, list):
            for item in content:
                item_type = item.get("type")
                if item_type == "text":
                    text_lines.append(f"{role}: {item.get('text', '')}")
                elif item_type == "image_url":
                    url = (item.get("image_url") or {}).get("url", "")
                    if url.startswith("data:") and ";base64," in url:
                        header, b64_data = url.split(",", 1)
                        mime_type = header.split(";")[0].replace("data:", "") or "image/png"
                        parts.append(Part.from_data(data=base64.b64decode(b64_data), mime_type=mime_type))

    prompt = "\n".join(line for line in text_lines if line.strip())
    if parts:
        return [prompt] + parts if prompt else parts
    return prompt


class _VertexSyncCompletions:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def _create_with_api_key(self, model_name: str, messages, max_completion_tokens: int, temperature: float):
        payload = {
            "contents": [],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_completion_tokens,
            },
        }

        for message in messages or []:
            role = message.get("role", "user")
            gemini_role = "model" if role == "assistant" else "user"
            content = message.get("content", "")

            if isinstance(content, str):
                text_value = content
            elif isinstance(content, list):
                text_parts = []
                for item in content:
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                text_value = "\n".join(part for part in text_parts if part)
            else:
                text_value = str(content)

            if text_value.strip():
                payload["contents"].append(
                    {
                        "role": gemini_role,
                        "parts": [{"text": text_value}],
                    }
                )

        if not payload["contents"]:
            payload["contents"] = [{"role": "user", "parts": [{"text": ""}]}]

        url = (
            f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model_name}:generateContent"
            f"?key={settings.VERTEX_API_KEY}"
        )

        with httpx.Client(timeout=45.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        candidates = data.get("candidates") or []
        if not candidates:
            return _make_compat_response("")

        parts = ((candidates[0].get("content") or {}).get("parts") or [])
        content = "\n".join(part.get("text", "") for part in parts if part.get("text"))
        return _make_compat_response(content)

    def create(self, model=None, messages=None, max_completion_tokens=1024, temperature=0.2, **kwargs):
        model_name = model or self.model_name

        if settings.VERTEX_API_KEY:
            return self._create_with_api_key(
                model_name=model_name,
                messages=messages,
                max_completion_tokens=max_completion_tokens,
                temperature=temperature,
            )

        vertex_model = GenerativeModel(model_name)
        payload = _build_vertex_payload(messages or [])
        response = vertex_model.generate_content(
            payload,
            generation_config=GenerationConfig(
                max_output_tokens=max_completion_tokens,
                temperature=temperature,
            ),
        )
        content = getattr(response, "text", "") or ""
        return _make_compat_response(content)


class _VertexAsyncCompletions:
    def __init__(self, model_name: str):
        self._sync = _VertexSyncCompletions(model_name)

    async def create(self, **kwargs):
        return await asyncio.to_thread(self._sync.create, **kwargs)


class _VertexSyncClient:
    def __init__(self, model_name: str):
        self.chat = SimpleNamespace(completions=_VertexSyncCompletions(model_name))


class _VertexAsyncClient:
    def __init__(self, model_name: str):
        self.chat = SimpleNamespace(completions=_VertexAsyncCompletions(model_name))


@lru_cache(maxsize=1)
def get_azure_openai_client() -> AzureOpenAI:
    if _is_vertex_provider():
        _validate_vertex_settings()
        if not settings.VERTEX_API_KEY:
            vertex_init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        return _VertexSyncClient(settings.AI_CHAT_MODEL)

    _validate_azure_openai_settings()
    return AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    )


@lru_cache(maxsize=1)
def get_async_azure_openai_client() -> AsyncAzureOpenAI:
    if _is_vertex_provider():
        _validate_vertex_settings()
        if not settings.VERTEX_API_KEY:
            vertex_init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        return _VertexAsyncClient(settings.AI_CHAT_MODEL)

    _validate_azure_openai_settings()
    return AsyncAzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
    )


def _fit_embedding_dimensions(vector: List[float], dimensions: int) -> List[float]:
    if dimensions <= 0:
        return vector
    if len(vector) == dimensions:
        return vector
    if len(vector) > dimensions:
        return vector[:dimensions]
    return vector + [0.0] * (dimensions - len(vector))


def get_text_embedding(text_to_embed: str) -> List[float]:
    if _is_vertex_provider():
        _validate_vertex_settings()
        vertex_init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
        model = TextEmbeddingModel.from_pretrained(settings.AI_EMBEDDING_MODEL)
        dimensions = settings.AI_EMBEDDING_DIMENSIONS
        embeddings = model.get_embeddings([text_to_embed])
        return _fit_embedding_dimensions(list(embeddings[0].values), dimensions)

    client = get_azure_openai_client()
    deployment = settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    dimensions = settings.AZURE_OPENAI_EMBEDDING_DIMENSIONS

    try:
        response = client.embeddings.create(
            model=deployment,
            input=text_to_embed,
            dimensions=dimensions,
        )
        return _fit_embedding_dimensions(response.data[0].embedding, dimensions)
    except Exception as first_error:
        logger.warning(
            f"Embedding call with dimensions failed for deployment '{deployment}': {first_error}. Retrying without dimensions."
        )
        response = client.embeddings.create(
            model=deployment,
            input=text_to_embed,
        )
        return _fit_embedding_dimensions(response.data[0].embedding, dimensions)


async def get_text_embedding_async(text_to_embed: str) -> List[float]:
    if _is_vertex_provider():
        return await asyncio.to_thread(get_text_embedding, text_to_embed)

    client = get_async_azure_openai_client()
    deployment = settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    dimensions = settings.AZURE_OPENAI_EMBEDDING_DIMENSIONS

    try:
        response = await client.embeddings.create(
            model=deployment,
            input=text_to_embed,
            dimensions=dimensions,
        )
        return _fit_embedding_dimensions(response.data[0].embedding, dimensions)
    except Exception as first_error:
        logger.warning(
            f"Async embedding call with dimensions failed for deployment '{deployment}': {first_error}. Retrying without dimensions."
        )
        response = await client.embeddings.create(
            model=deployment,
            input=text_to_embed,
        )
        return _fit_embedding_dimensions(response.data[0].embedding, dimensions)
