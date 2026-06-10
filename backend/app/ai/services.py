from typing import TypeVar

from pydantic import BaseModel

from app.ai.client import InferenceOptions, OllamaClient
from app.ai.parser import parse_structured_response
from app.ai.prompts import (
    STRUCTURED_JSON_SYSTEM,
    build_system_instruction,
    structured_output_prompt,
)
from app.core.config import get_settings

T = TypeVar("T", bound=BaseModel)


def get_ollama_client() -> OllamaClient:
    return OllamaClient(get_settings())


async def generate_text(
    prompt: str,
    *,
    system: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> str:
    """Send a prompt to Phi-3 (or configured model) and return plain text."""
    settings = get_settings()
    client = get_ollama_client()

    messages = [
        {"role": "system", "content": build_system_instruction(system)},
        {"role": "user", "content": prompt.strip()},
    ]

    options = InferenceOptions(
        temperature=temperature if temperature is not None else settings.ollama_temperature,
        max_tokens=max_tokens if max_tokens is not None else settings.ollama_max_tokens,
    )

    return await client.chat(messages=messages, options=options, model=model)


async def generate_structured(
    prompt: str,
    response_model: type[T],
    *,
    system: str | None = None,
    schema_hint: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
    max_parse_attempts: int | None = None,
) -> T:
    """Generate and validate structured JSON output using a Pydantic model."""
    settings = get_settings()
    hint = schema_hint or _schema_hint_from_model(response_model)
    full_prompt = structured_output_prompt(task=prompt, schema_hint=hint)

    raw = await generate_text(
        full_prompt,
        system=system or STRUCTURED_JSON_SYSTEM,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )

    return parse_structured_response(
        raw,
        response_model,
        max_parse_attempts=max_parse_attempts or settings.ollama_json_parse_retries,
    )


async def generate_structured_with_raw(
    prompt: str,
    response_model: type[T],
    *,
    system: str | None = None,
    schema_hint: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
    max_parse_attempts: int | None = None,
) -> tuple[str, T]:
    """Generate structured output and return both raw text and parsed model."""
    settings = get_settings()
    hint = schema_hint or _schema_hint_from_model(response_model)
    full_prompt = structured_output_prompt(task=prompt, schema_hint=hint)

    raw = await generate_text(
        full_prompt,
        system=system or STRUCTURED_JSON_SYSTEM,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )

    parsed = parse_structured_response(
        raw,
        response_model,
        max_parse_attempts=max_parse_attempts or settings.ollama_json_parse_retries,
    )
    return raw, parsed


def _schema_hint_from_model(model: type[BaseModel]) -> str:
    schema = model.model_json_schema()
    properties = schema.get("properties", {})
    fields = ", ".join(properties.keys()) if properties else "see schema"
    return f"{model.__name__}: {fields}"
