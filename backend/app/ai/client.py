from dataclasses import dataclass
from typing import Any

import httpx

from app.ai.exceptions import (
    OllamaConnectionError,
    OllamaInferenceError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)
from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class OllamaHealthStatus:
    reachable: bool
    model_available: bool
    model: str
    available_models: list[str]
    message: str


@dataclass(frozen=True)
class InferenceOptions:
    temperature: float
    max_tokens: int


class OllamaClient:
    """HTTP client for local Ollama inference."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self.base_url = self._settings.ollama_base_url.rstrip("/")
        self.model = self._settings.ollama_model
        self.timeout = self._settings.ollama_timeout_seconds
        self.max_retries = self._settings.ollama_max_retries

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, url, json=json)

                if response.status_code >= 400:
                    detail = response.text[:300]
                    raise OllamaInferenceError(
                        f"Ollama request failed ({response.status_code}): {detail}"
                    )

                return response.json()
            except httpx.TimeoutException as exc:
                last_error = OllamaTimeoutError(
                    f"Ollama request timed out after {self.timeout}s."
                )
            except httpx.RequestError as exc:
                last_error = OllamaConnectionError(
                    "Cannot connect to Ollama. Ensure Ollama is running locally."
                )
                last_error.__cause__ = exc
            except OllamaInferenceError:
                raise
            except Exception as exc:
                last_error = OllamaInferenceError(f"Unexpected Ollama error: {exc}")
                last_error.__cause__ = exc

            if attempt == self.max_retries and last_error:
                raise last_error

        raise OllamaConnectionError("Ollama request failed.")

    async def list_models(self) -> list[str]:
        payload = await self._request("GET", "/api/tags")
        models = payload.get("models") or []
        names: list[str] = []
        for item in models:
            name = item.get("name") or item.get("model")
            if name:
                names.append(name)
        return names

    def _model_matches(self, available: list[str], target: str) -> bool:
        target_lower = target.lower()
        for name in available:
            lowered = name.lower()
            if lowered == target_lower or lowered.startswith(f"{target_lower}:"):
                return True
        return False

    async def health_check(self) -> OllamaHealthStatus:
        try:
            models = await self.list_models()
            available = bool(models)
            model_available = self._model_matches(models, self.model) if available else False
            if not available:
                message = "Ollama is reachable but no models are installed."
            elif not model_available:
                message = (
                    f"Ollama is running, but model '{self.model}' was not found. "
                    f"Installed: {', '.join(models)}"
                )
            else:
                message = f"Ollama is healthy. Model '{self.model}' is available."

            return OllamaHealthStatus(
                reachable=True,
                model_available=model_available,
                model=self.model,
                available_models=models,
                message=message,
            )
        except (OllamaConnectionError, OllamaTimeoutError) as exc:
            return OllamaHealthStatus(
                reachable=False,
                model_available=False,
                model=self.model,
                available_models=[],
                message=str(exc),
            )
        except OllamaInferenceError as exc:
            return OllamaHealthStatus(
                reachable=False,
                model_available=False,
                model=self.model,
                available_models=[],
                message=str(exc),
            )

    async def ensure_model_available(self) -> None:
        status = await self.health_check()
        if not status.reachable:
            raise OllamaConnectionError(status.message)
        if not status.model_available:
            raise OllamaModelNotFoundError(status.message)

    async def chat(
        self,
        *,
        messages: list[dict[str, str]],
        options: InferenceOptions | None = None,
        model: str | None = None,
    ) -> str:
        await self.ensure_model_available()

        opts = options or InferenceOptions(
            temperature=self._settings.ollama_temperature,
            max_tokens=self._settings.ollama_max_tokens,
        )

        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": opts.temperature,
                "num_predict": opts.max_tokens,
            },
        }

        response = await self._request("POST", "/api/chat", json=payload)
        message = response.get("message") or {}
        content = (message.get("content") or "").strip()

        if not content:
            raise OllamaInferenceError("Ollama returned an empty response.")

        return content
