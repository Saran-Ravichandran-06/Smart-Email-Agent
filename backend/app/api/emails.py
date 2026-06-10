import logging
import traceback
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.classification import PRIORITY_LABELS

from app.auth.exceptions import OAuthTokenError
from app.auth.oauth import refresh_credentials_if_needed
from app.auth.session import get_current_user, get_current_user_with_token
from app.core.config import get_settings
from app.database.session import get_db
from app.gmail.client import GmailApiError
from app.models.email import Email
from app.models.user import User
from app.schemas.auth import EmailSyncResponse
from app.schemas.email import EmailResponse
from app.services.email_intelligence import run_post_sync_intelligence
from app.services.email_sync import sync_user_inbox
from app.services.gmail_auth_service import get_gmail_service_for_user

router = APIRouter(prefix="/emails", tags=["emails"])
logger = logging.getLogger(__name__)


@router.post("/sync", response_model=EmailSyncResponse)
async def sync_emails(
    user: User = Depends(get_current_user_with_token),
    db: Session = Depends(get_db),
) -> EmailSyncResponse:
    sync_started = perf_counter()
    settings = get_settings()
    print(
        "EMAIL SYNC STAGE [load authenticated user]:",
        {
            "user_id": user.id,
            "email": _mask_email(user.email),
            "google_id_present": bool(user.google_id),
        },
    )
    print(
        "EMAIL SYNC STAGE [load OAuth token]:",
        {
            "user_id": user.id,
            "token_present": user.oauth_token is not None,
            "access_token_present": bool(user.oauth_token.access_token) if user.oauth_token else False,
            "refresh_token_present": bool(user.oauth_token.refresh_token) if user.oauth_token else False,
            "token_expiry": user.oauth_token.token_expiry.isoformat()
            if user.oauth_token and user.oauth_token.token_expiry
            else None,
        },
    )

    is_mock_user = user.google_id == "mock_google_id" or user.email == "mock.user@gmail.com"
    if is_mock_user and settings.enable_mock_mode:
        from app.services.mock_email_seed import seed_mock_emails_and_relations

        synced, skipped, total_fetched = seed_mock_emails_and_relations(db, user.id)
        return EmailSyncResponse(
            message="Email sync completed (MOCK).",
            synced=synced,
            skipped=skipped,
            total_fetched=total_fetched,
        )

    try:
        print("EMAIL SYNC STAGE [refresh credentials if needed]: start")
        refresh_credentials_if_needed(db, user)
        print("EMAIL SYNC STAGE [refresh credentials if needed]: success")
    except OAuthTokenError as exc:
        _log_sync_stage_error("refresh credentials if needed", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _log_sync_stage_error("refresh credentials if needed", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "stage": "refresh_credentials_if_needed",
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            },
        ) from exc

    try:
        print("EMAIL SYNC STAGE [create Gmail service]: start")
        gmail_service = get_gmail_service_for_user(db, user)
        print("EMAIL SYNC STAGE [create Gmail service]: success")
    except OAuthTokenError as exc:
        _log_sync_stage_error("create Gmail service", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _log_sync_stage_error("create Gmail service", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "stage": "create_gmail_service",
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            },
        ) from exc

    try:
        sync_stage_started = perf_counter()
        print("EMAIL SYNC STAGE [sync user inbox]: start")
        result = sync_user_inbox(
            db,
            user,
            gmail_service,
            max_messages=settings.gmail_sync_max_results,
        )
        print(
            "EMAIL SYNC STAGE [sync user inbox]: success",
            {
                "synced": result.synced,
                "skipped": result.skipped,
                "total_fetched": result.total_fetched,
                "synced_email_ids": result.synced_email_ids,
                "duration_ms": round((perf_counter() - sync_stage_started) * 1000, 2),
            },
        )
    except OAuthTokenError as exc:
        _log_sync_stage_error("sync user inbox", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except GmailApiError as exc:
        _log_sync_stage_error("sync user inbox", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _log_sync_stage_error("sync user inbox", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "stage": "sync_user_inbox",
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            },
        ) from exc

    try:
        intelligence_started = perf_counter()
        print(
            "EMAIL SYNC STAGE [post-sync intelligence]: start",
            {"synced_email_ids": result.synced_email_ids},
        )
        intelligence = await run_post_sync_intelligence(
            db,
            user,
            synced_email_ids=result.synced_email_ids,
        )
        print(
            "EMAIL SYNC STAGE [post-sync intelligence]: success",
            {
                "emails": len(intelligence.email_ids),
                "classified": intelligence.priority.classified if intelligence.priority else 0,
                "tasks_created": intelligence.tasks.tasks_created if intelligence.tasks else 0,
                "followups_created": intelligence.followups.created,
                "followups_updated": intelligence.followups.updated,
                "followups_cleared": intelligence.followups.cleared,
                "duration_ms": round((perf_counter() - intelligence_started) * 1000, 2),
            },
        )
    except Exception as exc:
        _log_sync_stage_error("post-sync intelligence", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "stage": "post_sync_intelligence",
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            },
        ) from exc

    print(
        "EMAIL SYNC TOTAL:",
        {
            "duration_ms": round((perf_counter() - sync_started) * 1000, 2),
            "synced": result.synced,
            "skipped": result.skipped,
            "total_fetched": result.total_fetched,
        },
    )
    return EmailSyncResponse(
        message="Email sync completed.",
        synced=result.synced,
        skipped=result.skipped,
        total_fetched=result.total_fetched,
    )


def _mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[:1]}...@{domain}"
    return f"{local[:2]}...{local[-1:]}@{domain}"


def _log_sync_stage_error(stage: str, exc: Exception) -> None:
    print(f"EMAIL SYNC STAGE ERROR [{stage}]:", exc.__class__.__name__, str(exc))
    traceback.print_exc()
    logger.exception("Email sync failed during %s", stage)


@router.get("", response_model=list[EmailResponse])
def list_emails(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    priority: str | None = Query(
        default=None,
        description=f"Filter by priority: {', '.join(PRIORITY_LABELS)}",
    ),
) -> list[Email]:
    if priority is not None:
        normalized = priority.strip().lower()
        if normalized not in PRIORITY_LABELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority. Use one of: {', '.join(PRIORITY_LABELS)}",
            )

    query = db.query(Email).filter(
        Email.user_id == user.id,
        Email.gmail_deleted_at.is_(None),
    )
    if priority is not None:
        query = query.filter(Email.priority == normalized)

    emails = query.order_by(Email.received_at.desc()).all()
    print(
        "EMAIL API DB QUERY [list emails]:",
        {
            "user_id": user.id,
            "priority_filter": priority,
            "email_ids": [email.id for email in emails],
            "priorities": {email.id: email.priority for email in emails},
        },
    )
    return emails


@router.get("/{email_id}", response_model=EmailResponse)
def get_email(
    email_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Email:
    email = (
        db.query(Email)
        .filter(Email.id == email_id, Email.user_id == user.id)
        .first()
    )
    print(
        "EMAIL API DB QUERY [get email]:",
        {
            "user_id": user.id,
            "email_id": email_id,
            "found": email is not None,
            "priority": email.priority if email else None,
            "has_cleaned_body": bool(email.body_cleaned) if email else False,
            "cleaned_body_chars": len(email.body_cleaned or "") if email else 0,
        },
    )
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found.",
        )
    return email
