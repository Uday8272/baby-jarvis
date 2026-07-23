from dataclasses import dataclass
from typing import Protocol

import httpx

from backend.config import Settings


@dataclass(frozen=True)
class LLMGenerationRequest:
    prompt: str
    temperature: float = 0.2
    max_output_tokens: int = 512


class AsyncLLMService(Protocol):
    async def generate_text(self, request: LLMGenerationRequest) -> str:
        ...


class GeminiService:
    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini.")

        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_model
        self._timeout_seconds = settings.llm_timeout_seconds

    async def generate_text(self, request: LLMGenerationRequest) -> str:
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent?key={self._api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_output_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            body = response.json()

        candidates = body.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")

        parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
        text = "".join(text_chunks).strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return text


def get_llm_service(settings: Settings) -> AsyncLLMService:
    provider = settings.llm_provider.lower()

    if provider == "gemini":
        return GeminiService(settings)

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
