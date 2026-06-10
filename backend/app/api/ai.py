from fastapi import APIRouter, HTTPException, status

from app.ai.exceptions import (
    AIResponseParseError,
    OllamaConnectionError,
    OllamaInferenceError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)
from app.ai.services import generate_structured_with_raw, generate_text, get_ollama_client
from app.core.config import get_settings
from app.schemas.ai import (
    AITestPromptRequest,
    AITestPromptResponse,
    AITestStructuredRequest,
    AITestStructuredResponse,
    OllamaHealthResponse,
    SampleStructuredResult,
)

router = APIRouter(prefix="/ai", tags=["ai"])


def _require_dev_endpoints_enabled() -> None:
    settings = get_settings()
    if not settings.enable_dev_endpoints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development AI test endpoints are disabled.",
        )


def _ai_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, (OllamaConnectionError, OllamaModelNotFoundError)):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    if isinstance(exc, OllamaTimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    if isinstance(exc, AIResponseParseError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if isinstance(exc, OllamaInferenceError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected AI infrastructure error.",
    )


@router.get("/health", response_model=OllamaHealthResponse)
async def ollama_health() -> OllamaHealthResponse:
    client = get_ollama_client()
    result = await client.health_check()
    return OllamaHealthResponse(
        reachable=result.reachable,
        model_available=result.model_available,
        model=result.model,
        available_models=result.available_models,
        message=result.message,
    )


@router.post("/test", response_model=AITestPromptResponse)
async def test_prompt(payload: AITestPromptRequest) -> AITestPromptResponse:
    _require_dev_endpoints_enabled()
    settings = get_settings()
    try:
        response = await generate_text(
            payload.prompt,
            system=payload.system,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
    except Exception as exc:
        raise _ai_http_exception(exc) from exc

    return AITestPromptResponse(model=settings.ollama_model, response=response)


@router.post("/test/structured", response_model=AITestStructuredResponse)
async def test_structured_response(
    payload: AITestStructuredRequest,
) -> AITestStructuredResponse:
    _require_dev_endpoints_enabled()
    settings = get_settings()
    prompt = (
        "Classify the text into one label: positive, neutral, or negative. "
        "Return JSON with keys: label, confidence (0 to 1), reason.\n\n"
        f"Text: {payload.text}"
    )
    schema_hint = (
        '{"label": "positive|neutral|negative", '
        '"confidence": 0.0, "reason": "short explanation"}'
    )

    try:
        raw, parsed = await generate_structured_with_raw(
            prompt,
            SampleStructuredResult,
            schema_hint=schema_hint,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
    except Exception as exc:
        raise _ai_http_exception(exc) from exc

    return AITestStructuredResponse(
        model=settings.ollama_model,
        raw_response=raw,
        parsed=parsed,
    )
