import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session, joinedload

from app.auth.oauth import create_oauth_flow, save_credentials_for_user, upsert_user_from_google
from app.auth.session import clear_session, get_current_user, set_session_user
from app.core.config import GMAIL_SCOPES, get_settings
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import AuthUserResponse, OAuthCallbackResponse
from app.services.gmail_auth_service import fetch_google_user_profile

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/google/login")
def google_login(
    request: Request,
    redirect: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    try:
        settings.require_google_oauth()
    except ValueError as exc:
        if settings.enable_mock_mode:
            from app.models.oauth_token import OAuthToken
            user = upsert_user_from_google(
                db,
                google_id="mock_google_id",
                email="mock.user@gmail.com",
                name="Mock Developer",
            )
            token_record = user.oauth_token
            if token_record is None:
                token_record = OAuthToken(
                    user_id=user.id,
                    access_token="mock_access_token",
                    refresh_token="mock_refresh_token",
                )
                db.add(token_record)
                db.commit()
                db.refresh(user)

            set_session_user(request, user.id)

            if redirect == "frontend":
                return RedirectResponse(url=f"{settings.frontend_url}/?oauth=success")
            return RedirectResponse(url="/api/auth/me")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"{exc} Set ENABLE_MOCK_MODE=true only for local mock development, "
                "or configure real Google OAuth credentials."
            ),
        ) from exc

    flow = create_oauth_flow(settings)
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["oauth_state"] = state
    code_verifier = getattr(flow, "code_verifier", None)
    if code_verifier:
        request.session["oauth_code_verifier"] = code_verifier
    print(
        "GOOGLE OAUTH LOGIN PKCE:",
        {
            "state_saved": bool(state),
            "code_verifier_saved": bool(code_verifier),
            "requested_scopes": GMAIL_SCOPES,
        },
    )
    if redirect == "frontend":
        request.session["post_oauth_redirect"] = "frontend"
    return RedirectResponse(url=authorization_url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: Session = Depends(get_db),
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    redirect: str | None = None,
):
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code from Google.",
        )

    expected_state = request.session.pop("oauth_state", None)
    code_verifier = request.session.pop("oauth_code_verifier", None)
    session_redirect = request.session.pop("post_oauth_redirect", None)
    state_valid = bool(expected_state and state and expected_state == state)
    print(
        "GOOGLE OAUTH STATE VALIDATION:",
        {
            "state_provided": bool(state),
            "expected_state_present": bool(expected_state),
            "valid": state_valid,
            "code_verifier_present": bool(code_verifier),
        },
    )
    if not expected_state or not state or expected_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state. Please try logging in again.",
        )

    settings = get_settings()
    try:
        flow: Flow = create_oauth_flow(settings)
        if code_verifier:
            flow.code_verifier = code_verifier
        print(
            "GOOGLE TOKEN EXCHANGE CONFIG:",
            {
                "redirect_uri": settings.google_redirect_uri,
                "client_id": _mask_client_id(settings.google_client_id),
                "token_uri": settings.google_client_config["web"]["token_uri"],
                "code_verifier_restored": bool(code_verifier),
            },
        )
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials
    except Warning as exc:
        credentials = flow.credentials
        granted_scopes = _get_granted_scopes(credentials)
        equivalent_warning = _scope_warning_is_equivalent(exc, GMAIL_SCOPES, granted_scopes)
        print(
            "GOOGLE TOKEN EXCHANGE SCOPE WARNING:",
            {
                "message": str(exc),
                "equivalent_scope_normalization": equivalent_warning,
                "granted_scopes": granted_scopes,
                "credentials_available": credentials is not None,
            },
        )
        if not equivalent_warning or not credentials or not credentials.token:
            google_error = _extract_google_error(exc)
            print("GOOGLE TOKEN EXCHANGE ERROR:", repr(exc))
            print("GOOGLE TOKEN ENDPOINT RESPONSE:", google_error)
            logger.exception(
                "Google OAuth token exchange scope warning is not safely recoverable. "
                "requested_scopes=%s granted_scopes=%s",
                GMAIL_SCOPES,
                granted_scopes,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": str(exc),
                    "error_type": exc.__class__.__name__,
                    "google_error": google_error,
                },
            ) from exc
    except Exception as exc:
        google_error = _extract_google_error(exc)
        print("GOOGLE TOKEN EXCHANGE ERROR:", repr(exc))
        print("GOOGLE TOKEN ENDPOINT RESPONSE:", google_error)
        logger.exception(
            "Google OAuth token exchange failed. redirect_uri=%s client_id=%s google_error=%s",
            settings.google_redirect_uri,
            _mask_client_id(settings.google_client_id),
            google_error,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": str(exc),
                "error_type": exc.__class__.__name__,
                "google_error": google_error,
            },
        ) from exc

    try:
        if not credentials or not credentials.token:
            raise ValueError("Google did not return valid credentials.")
        print(
            "GOOGLE TOKEN EXCHANGE SUCCESS:",
            {
                "has_access_token": bool(credentials.token),
                "has_refresh_token": bool(credentials.refresh_token),
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                "requested_scopes": GMAIL_SCOPES,
                "granted_scopes": _get_granted_scopes(credentials),
                "valid": credentials.valid,
                "expired": credentials.expired,
            },
        )
    except Exception as exc:
        _log_callback_stage_error("token exchange success validation", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "stage": "token_exchange_success_validation",
                "message": str(exc),
                "error_type": exc.__class__.__name__,
            },
        ) from exc

    try:
        print("GOOGLE USER INFO FETCH START:", {"has_access_token": bool(credentials.token)})
        profile = await fetch_google_user_profile(credentials.token)
        print(
            "GOOGLE USER INFO FETCH SUCCESS:",
            {
                "profile_keys": sorted(profile.keys()),
                "has_sub": bool(profile.get("sub")),
                "has_id": bool(profile.get("id")),
                "email": _mask_email(profile.get("email")),
                "has_name": bool(profile.get("name")),
            },
        )
    except Exception as exc:
        _log_callback_stage_error("user info fetch", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "stage": "user_info_fetch",
                "message": str(exc),
                "error_type": exc.__class__.__name__,
                "google_error": _extract_google_error(exc),
            },
        ) from exc

    try:
        print("GOOGLE PROFILE KEYS:", {"profile_keys": sorted(profile.keys())})
        google_id = profile.get("sub") or profile.get("id")
        email = profile.get("email")
        name = profile.get("name")

        if not google_id or not email:
            raise ValueError("Google profile is missing required user information.")
        print(
            "GOOGLE PROFILE VALIDATION SUCCESS:",
            {
                "has_google_id": bool(google_id),
                "google_id_source": "sub" if profile.get("sub") else "id",
                "email": _mask_email(email),
                "has_name": bool(name),
            },
        )
    except Exception as exc:
        _log_callback_stage_error("profile validation", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "stage": "profile_validation",
                "message": str(exc),
                "error_type": exc.__class__.__name__,
            },
        ) from exc

    try:
        print(
            "GOOGLE USER UPSERT START:",
            {
                "google_id_present": bool(google_id),
                "email": _mask_email(email),
            },
        )
        user = upsert_user_from_google(
            db,
            google_id=str(google_id),
            email=email,
            name=name,
        )
        print("GOOGLE USER UPSERT SUCCESS:", {"user_id": user.id, "email": _mask_email(user.email)})
    except Exception as exc:
        _log_callback_stage_error("user creation/update", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "stage": "user_creation_update",
                "message": str(exc),
                "error_type": exc.__class__.__name__,
            },
        ) from exc

    try:
        print(
            "GOOGLE OAUTH TOKEN SAVE START:",
            {
                "user_id": user.id,
                "has_access_token": bool(credentials.token),
                "has_refresh_token": bool(credentials.refresh_token),
            },
        )
        save_credentials_for_user(db, user, credentials)
        print("GOOGLE OAUTH TOKEN SAVE SUCCESS:", {"user_id": user.id})
    except Exception as exc:
        _log_callback_stage_error("OAuth token save", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "stage": "oauth_token_save",
                "message": str(exc),
                "error_type": exc.__class__.__name__,
            },
        ) from exc

    try:
        print("GOOGLE SESSION CREATE START:", {"user_id": user.id})
        set_session_user(request, user.id)
        print("GOOGLE SESSION CREATE SUCCESS:", {"user_id": user.id})
    except Exception as exc:
        _log_callback_stage_error("session creation", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "stage": "session_creation",
                "message": str(exc),
                "error_type": exc.__class__.__name__,
            },
        ) from exc

    try:
        print("GOOGLE AUTH USER RELOAD START:", {"user_id": user.id})
        user = (
            db.query(User)
            .options(joinedload(User.oauth_token))
            .filter(User.id == user.id)
            .one()
        )
        print(
            "GOOGLE AUTH USER RELOAD SUCCESS:",
            {
                "user_id": user.id,
                "gmail_connected": user.oauth_token is not None,
            },
        )
    except Exception as exc:
        _log_callback_stage_error("authenticated user reload", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "stage": "authenticated_user_reload",
                "message": str(exc),
                "error_type": exc.__class__.__name__,
            },
        ) from exc

    settings = get_settings()
    if redirect == "frontend" or session_redirect == "frontend":
        try:
            redirect_url = f"{settings.frontend_url}/?oauth=success"
            print("GOOGLE FRONTEND REDIRECT:", {"url": redirect_url})
            return RedirectResponse(url=redirect_url)
        except Exception as exc:
            _log_callback_stage_error("frontend redirect", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "stage": "frontend_redirect",
                    "message": str(exc),
                    "error_type": exc.__class__.__name__,
                },
            ) from exc

    return OAuthCallbackResponse(
        message="Google authentication successful.",
        user=_to_auth_user(user),
    )


@router.get("/me", response_model=AuthUserResponse)
def auth_me(user: User = Depends(get_current_user)) -> AuthUserResponse:
    return _to_auth_user(user)


@router.post("/logout")
def logout(request: Request) -> dict[str, str]:
    clear_session(request)
    return {"message": "Logged out successfully."}


def _to_auth_user(user: User) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        google_id=user.google_id,
        gmail_connected=user.oauth_token is not None,
    )


def _mask_client_id(client_id: str | None) -> str | None:
    if not client_id:
        return None
    if len(client_id) <= 12:
        return f"{client_id[:4]}..."
    return f"{client_id[:8]}...{client_id[-8:]}"


def _mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = f"{local[:1]}..."
    else:
        masked_local = f"{local[:2]}...{local[-1:]}"
    return f"{masked_local}@{domain}"


def _get_granted_scopes(credentials) -> list[str]:
    if not credentials:
        return []
    scopes = getattr(credentials, "granted_scopes", None) or getattr(credentials, "scopes", None) or []
    return list(scopes)


def _normalize_google_scope(scope: str) -> str:
    equivalents = {
        "email": "https://www.googleapis.com/auth/userinfo.email",
        "profile": "https://www.googleapis.com/auth/userinfo.profile",
    }
    return equivalents.get(scope, scope)


def _normalize_google_scopes(scopes: list[str]) -> set[str]:
    return {_normalize_google_scope(scope) for scope in scopes}


def _scope_warning_is_equivalent(
    warning: Warning,
    requested_scopes: list[str],
    granted_scopes: list[str],
) -> bool:
    message = str(warning)
    if "Scope has changed" not in message:
        return False

    normalized_requested = _normalize_google_scopes(requested_scopes)
    normalized_granted = _normalize_google_scopes(granted_scopes)
    return bool(normalized_granted) and normalized_requested.issubset(normalized_granted)


def _log_callback_stage_error(stage: str, exc: Exception) -> None:
    print(f"GOOGLE CALLBACK STAGE ERROR [{stage}]:", repr(exc))
    traceback.print_exc()
    logger.exception("Google OAuth callback failed during %s", stage)


def _extract_google_error(exc: Exception) -> dict[str, object]:
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
        "exception": repr(exc),
        "message": str(exc),
        "oauth_error": getattr(exc, "error", None),
        "oauth_description": getattr(exc, "description", None),
        "oauth_uri": getattr(exc, "uri", None),
        "status_code": getattr(exc, "status_code", None) or response_status,
        "response_json": response_json,
        "response_text": response_text,
    }
