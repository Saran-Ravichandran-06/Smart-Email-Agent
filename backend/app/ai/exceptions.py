class AIError(Exception):
    """Base AI layer error."""


class OllamaConnectionError(AIError):
    """Ollama server is unreachable."""


class OllamaModelNotFoundError(AIError):
    """Requested model is not available in Ollama."""


class OllamaTimeoutError(AIError):
    """Ollama request timed out."""


class OllamaInferenceError(AIError):
    """Ollama returned an error during inference."""


class AIResponseParseError(AIError):
    """Failed to parse or validate model output."""
