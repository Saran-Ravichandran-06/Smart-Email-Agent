import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.exceptions import AIResponseParseError

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE_PATTERN = re.compile(
    r"```(?:json)?\s*([\s\S]*?)\s*```",
    re.IGNORECASE,
)
_JSON_OBJECT_PATTERN = re.compile(r"\{[\s\S]*\}")
_JSON_ARRAY_PATTERN = re.compile(r"\[[\s\S]*\]")


def strip_json_fences(text: str) -> str:
    if not text:
        return ""
    match = _JSON_FENCE_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def extract_json_payload(text: str) -> Any:
    """Extract a JSON object or array from model text output."""
    if not text or not text.strip():
        raise AIResponseParseError("Model returned an empty response.")

    candidates = [text.strip(), strip_json_fences(text)]

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        object_match = _JSON_OBJECT_PATTERN.search(candidate)
        if object_match:
            try:
                return json.loads(object_match.group(0))
            except json.JSONDecodeError:
                pass

        array_match = _JSON_ARRAY_PATTERN.search(candidate)
        if array_match:
            try:
                return json.loads(array_match.group(0))
            except json.JSONDecodeError:
                pass

    raise AIResponseParseError("Could not extract valid JSON from model response.")


def validate_json_model(payload: Any, model: type[T]) -> T:
    try:
        if isinstance(payload, dict):
            return model.model_validate(payload)
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            return model.model_validate(payload[0])
        return model.model_validate(payload)
    except ValidationError as exc:
        raise AIResponseParseError(f"JSON validation failed: {exc}") from exc


def parse_structured_response(
    text: str,
    model: type[T],
    *,
    max_parse_attempts: int = 3,
) -> T:
    """
    Parse model text into a Pydantic object.

    Retries parsing only (not inference) by progressively narrowing extraction.
    """
    last_error: Exception | None = None
    candidates = [text, strip_json_fences(text)]

    for attempt in range(max_parse_attempts):
        candidate = candidates[min(attempt, len(candidates) - 1)]
        try:
            payload = extract_json_payload(candidate)
            return validate_json_model(payload, model)
        except (AIResponseParseError, ValidationError) as exc:
            last_error = exc

    raise AIResponseParseError(
        f"Failed to parse structured response after {max_parse_attempts} attempts."
    ) from last_error
