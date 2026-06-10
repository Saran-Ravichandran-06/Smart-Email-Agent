import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GMAIL_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]


def _parse_cors_origins(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes", "on")


def _build_database_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "email_agent")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def _load_google_credentials_from_file(path: str) -> tuple[str | None, str | None]:
    file_path = Path(path)
    if not file_path.is_file():
        return None, None

    with file_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    for key in ("web", "installed"):
        section = data.get(key)
        if section:
            return section.get("client_id"), section.get("client_secret")

    return None, None


class Settings:
    """Application settings loaded from environment variables."""

    app_name: str = os.getenv("APP_NAME", "Smart Email Agent API")
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = _parse_bool(os.getenv("DEBUG"))
    enable_mock_mode: bool = _parse_bool(os.getenv("ENABLE_MOCK_MODE"))
    enable_dev_endpoints: bool = _parse_bool(os.getenv("ENABLE_DEV_ENDPOINTS"))
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    cors_origins: list[str] = _parse_cors_origins(
        os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
    )
    database_url: str = _build_database_url()

    session_secret_key: str = os.getenv(
        "SESSION_SECRET_KEY",
        "change-me-in-production-use-a-long-random-string",
    )
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    google_credentials_path: str | None = os.getenv("GOOGLE_CREDENTIALS_PATH")
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret: str | None = os.getenv("GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/callback",
    )

    gmail_sync_max_results: int = int(os.getenv("GMAIL_SYNC_MAX_RESULTS", "50"))

    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "phi3")
    ollama_timeout_seconds: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))
    ollama_max_retries: int = int(os.getenv("OLLAMA_MAX_RETRIES", "2"))
    ollama_temperature: float = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
    ollama_max_tokens: int = int(os.getenv("OLLAMA_MAX_TOKENS", "512"))
    ollama_json_parse_retries: int = int(os.getenv("OLLAMA_JSON_PARSE_RETRIES", "3"))

    followup_stale_hours: int = int(os.getenv("FOLLOWUP_STALE_HOURS", "48"))
    followup_priority_stale_hours: int = int(os.getenv("FOLLOWUP_PRIORITY_STALE_HOURS", "24"))

    def __init__(self) -> None:
        file_client_id, file_client_secret = (None, None)
        if self.google_credentials_path:
            file_client_id, file_client_secret = _load_google_credentials_from_file(
                self.google_credentials_path
            )

        self.google_client_id = self.google_client_id or file_client_id
        self.google_client_secret = self.google_client_secret or file_client_secret

    def require_google_oauth(self) -> tuple[str, str]:
        if not self.google_client_id or not self.google_client_secret:
            raise ValueError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET, or provide GOOGLE_CREDENTIALS_PATH."
            )
        return self.google_client_id, self.google_client_secret

    @property
    def google_client_config(self) -> dict:
        client_id, client_secret = self.require_google_oauth()
        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.google_redirect_uri],
            }
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
