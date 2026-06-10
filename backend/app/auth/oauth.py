import json
from datetime import datetime, timedelta, timezone

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

from app.auth.exceptions import OAuthTokenError
from app.core.config import GMAIL_SCOPES, Settings, get_settings
from app.models.oauth_token import OAuthToken
from app.models.user import User

# Allow OAuth over HTTP for local development only.
import os

if os.getenv("APP_ENV", "development") == "development":
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")


def create_oauth_flow(settings: Settings | None = None) -> Flow:
    settings = settings or get_settings()
    return Flow.from_client_config(
        settings.google_client_config,
        scopes=GMAIL_SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )


def credentials_from_token_record(
    token_record: OAuthToken,
    settings: Settings | None = None,
) -> Credentials:
    settings = settings or get_settings()
    try:
        client_id, client_secret = settings.require_google_oauth()
    except ValueError:
        if settings.enable_mock_mode:
            client_id, client_secret = "mock_client_id", "mock_client_secret"
        else:
            raise

    normalized_expiry = normalize_credentials_expiry(token_record.token_expiry)
    print(
        "OAUTH TOKEN EXPIRY LOAD:",
        {
            "token_id": token_record.id,
            "original": _datetime_debug_value(token_record.token_expiry),
            "normalized": _datetime_debug_value(normalized_expiry),
            "stored_scopes": get_token_scopes(token_record),
            "configured_scopes": GMAIL_SCOPES,
        },
    )

    return Credentials(
        token=token_record.access_token,
        refresh_token=token_record.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=GMAIL_SCOPES,
        expiry=normalized_expiry,
    )


def save_credentials_for_user(
    db: Session,
    user: User,
    credentials: Credentials,
) -> OAuthToken:
    token_record = user.oauth_token
    if token_record is None:
        token_record = OAuthToken(user_id=user.id)
        db.add(token_record)

    existing_refresh_token_present = bool(token_record.refresh_token)
    incoming_refresh_token_present = bool(credentials.refresh_token)
    granted_scopes = get_credentials_scopes(credentials)
    token_record.access_token = credentials.token
    if credentials.refresh_token:
        token_record.refresh_token = credentials.refresh_token
    if granted_scopes:
        token_record.scopes = json.dumps(sorted(normalize_scope_set(granted_scopes)))
    normalized_expiry = normalize_credentials_expiry(credentials.expiry)
    print(
        "OAUTH TOKEN EXPIRY SAVE:",
        {
            "user_id": user.id,
            "original": _datetime_debug_value(credentials.expiry),
            "normalized": _datetime_debug_value(normalized_expiry),
            "incoming_refresh_token_present": incoming_refresh_token_present,
            "existing_refresh_token_present": existing_refresh_token_present,
            "stored_refresh_token_present": bool(token_record.refresh_token),
            "granted_scopes": granted_scopes,
            "stored_scopes": get_token_scopes(token_record),
        },
    )
    token_record.token_expiry = normalized_expiry

    db.commit()
    db.refresh(token_record)
    db.refresh(user)
    return token_record


def refresh_credentials_if_needed(
    db: Session,
    user: User,
    settings: Settings | None = None,
) -> Credentials:
    settings = settings or get_settings()
    token_record = user.oauth_token
    if token_record is None:
        raise OAuthTokenError("No OAuth token stored for user.")

    print(
        "OAUTH REFRESH TOKEN STATE:",
        {
            "user_id": user.id,
            "access_token_present": bool(token_record.access_token),
            "refresh_token_present": bool(token_record.refresh_token),
            "token_expiry": _datetime_debug_value(token_record.token_expiry),
            "stored_scopes": get_token_scopes(token_record),
            "required_scopes": GMAIL_SCOPES,
        },
    )
    if not token_has_required_scopes(token_record):
        invalidate_oauth_token(
            db,
            user,
            reason="stored token scope set is missing or does not include the current Gmail scopes",
        )
        raise OAuthTokenError(
            "Google authorization must be renewed because the stored refresh token "
            "was created with an older or unknown scope set. Please log in with Google again."
        )

    credentials = credentials_from_token_record(token_record, settings)

    needs_refresh = credentials_need_refresh(credentials.expiry, bool(credentials.token))
    print(
        "OAUTH TOKEN EXPIRY CHECK RESULT:",
        {
            "user_id": user.id,
            "expiry": _datetime_debug_value(credentials.expiry),
            "needs_refresh": needs_refresh,
        },
    )

    if needs_refresh:
        if not credentials.refresh_token:
            print(
                "OAUTH TOKEN REFRESH SKIPPED:",
                {"user_id": user.id, "reason": "missing refresh token"},
            )
            raise OAuthTokenError(
                "Access token expired and no refresh token is available. "
                "Please log in again."
            )
        try:
            print(
                "OAUTH TOKEN REFRESH ATTEMPT:",
                {
                    "user_id": user.id,
                    "refresh_token_present": bool(credentials.refresh_token),
                    "expiry_before": _datetime_debug_value(credentials.expiry),
                },
            )
            credentials.refresh(Request())
            print(
                "OAUTH TOKEN REFRESH SUCCESS:",
                {
                    "user_id": user.id,
                    "access_token_present": bool(credentials.token),
                    "refresh_token_present": bool(credentials.refresh_token),
                    "expiry_after": _datetime_debug_value(credentials.expiry),
                    "valid": credentials.valid,
                    "expired": credentials.expired,
                },
            )
        except Exception as exc:
            refresh_error = _extract_refresh_error(exc)
            print(
                "OAUTH TOKEN REFRESH ERROR:",
                {
                    "user_id": user.id,
                    "error_type": exc.__class__.__name__,
                    "message": str(exc),
                    "response": refresh_error,
                },
            )
            if is_invalid_scope_error(exc, refresh_error):
                invalidate_oauth_token(
                    db,
                    user,
                    reason="Google rejected refresh with invalid_scope",
                )
                raise OAuthTokenError(
                    "Google authorization must be renewed because the stored refresh token "
                    "does not match the current Gmail scopes. Please log in with Google again."
                ) from exc
            raise OAuthTokenError(f"Failed to refresh Google access token: {exc}") from exc
        save_credentials_for_user(db, user, credentials)

    return credentials


def credentials_need_refresh(expiry: datetime | None, has_access_token: bool) -> bool:
    if not has_access_token:
        return True
    if expiry is None:
        return False
    normalized = normalize_credentials_expiry(expiry)
    if normalized is None:
        return False
    return normalized <= datetime.utcnow() + timedelta(minutes=5)


def get_credentials_scopes(credentials: Credentials) -> list[str]:
    scopes = getattr(credentials, "granted_scopes", None) or getattr(credentials, "scopes", None) or []
    return [str(scope) for scope in scopes]


def normalize_scope(scope: str) -> str:
    equivalents = {
        "email": "https://www.googleapis.com/auth/userinfo.email",
        "profile": "https://www.googleapis.com/auth/userinfo.profile",
    }
    return equivalents.get(scope, scope)


def normalize_scope_set(scopes: list[str] | set[str]) -> set[str]:
    return {normalize_scope(str(scope)) for scope in scopes if str(scope).strip()}


def get_token_scopes(token_record: OAuthToken) -> list[str]:
    if not token_record.scopes:
        return []
    try:
        parsed = json.loads(token_record.scopes)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(scope) for scope in parsed]


def token_has_required_scopes(token_record: OAuthToken) -> bool:
    stored = normalize_scope_set(get_token_scopes(token_record))
    required = normalize_scope_set(GMAIL_SCOPES)
    return bool(stored) and required.issubset(stored)


def invalidate_oauth_token(db: Session, user: User, *, reason: str) -> None:
    token_record = user.oauth_token
    if token_record is None:
        return
    print(
        "OAUTH TOKEN INVALIDATED:",
        {
            "user_id": user.id,
            "reason": reason,
            "stored_scopes": get_token_scopes(token_record),
            "required_scopes": GMAIL_SCOPES,
        },
    )
    db.delete(token_record)
    db.commit()
    user.oauth_token = None


def upsert_user_from_google(
    db: Session,
    *,
    google_id: str,
    email: str,
    name: str | None,
) -> User:
    user = db.query(User).filter(User.google_id == google_id).first()
    if user is None:
        user = db.query(User).filter(User.email == email).first()

    if user is None:
        user = User(email=email, name=name, google_id=google_id)
        db.add(user)
    else:
        user.email = email
        user.name = name or user.name
        user.google_id = google_id

    db.commit()
    db.refresh(user)
    return user


def expiry_from_credentials(credentials: Credentials) -> datetime | None:
    return normalize_credentials_expiry(credentials.expiry)


def normalize_credentials_expiry(expiry: datetime | None) -> datetime | None:
    """Return UTC as a timezone-naive datetime for google-auth expiry checks."""
    if expiry is None:
        return None
    if expiry.tzinfo is None:
        return expiry
    return expiry.astimezone(timezone.utc).replace(tzinfo=None)


def _datetime_debug_value(value: datetime | None) -> dict[str, str | None]:
    if value is None:
        return {"iso": None, "tzinfo": None, "utcoffset": None}
    offset = value.utcoffset()
    return {
        "iso": value.isoformat(),
        "tzinfo": str(value.tzinfo),
        "utcoffset": str(offset) if offset is not None else None,
    }


def _extract_refresh_error(exc: Exception) -> dict[str, object]:
    response = getattr(exc, "response", None)
    response_text = None
    response_status = None
    response_json = None
    if response is not None:
        response_status = getattr(response, "status_code", None)
        response_text = getattr(response, "text", None)
        try:
            response_json = response.json()
        except Exception:
            response_json = None
    return {
        "status_code": response_status,
        "response_json": response_json,
        "response_text": response_text,
    }


def is_invalid_scope_error(exc: Exception, refresh_error: dict[str, object]) -> bool:
    text = str(exc).lower()
    response_text = str(refresh_error.get("response_text") or "").lower()
    response_json = refresh_error.get("response_json")
    if isinstance(response_json, dict):
        error = str(response_json.get("error") or "").lower()
        description = str(response_json.get("error_description") or "").lower()
        if "invalid_scope" in error or "invalid_scope" in description:
            return True
    return "invalid_scope" in text or "invalid_scope" in response_text
