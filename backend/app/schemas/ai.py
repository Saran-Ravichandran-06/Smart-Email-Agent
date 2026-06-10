from pydantic import BaseModel, Field


class OllamaHealthResponse(BaseModel):
    reachable: bool
    model_available: bool
    model: str
    available_models: list[str]
    message: str


class AITestPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    system: str | None = Field(default=None, max_length=2000)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=16, le=2048)


class AITestPromptResponse(BaseModel):
    model: str
    response: str


class SampleStructuredResult(BaseModel):
    """Example schema for infrastructure JSON validation tests."""

    label: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class AITestStructuredRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=16, le=2048)


class AITestStructuredResponse(BaseModel):
    model: str
    raw_response: str
    parsed: SampleStructuredResult
