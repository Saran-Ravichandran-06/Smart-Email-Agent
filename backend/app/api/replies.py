from datetime import datetime, timezone
from email.utils import parseaddr

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.exceptions import (
    OllamaConnectionError,
    OllamaInferenceError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)
from app.ai.reply_generation import REPLY_TONES
from app.auth.exceptions import OAuthTokenError
from app.auth.oauth import get_token_scopes, refresh_credentials_if_needed
from app.core.config import GMAIL_SCOPES
from app.auth.session import get_current_user, get_current_user_with_token
from app.database.session import get_db
from app.gmail.client import GmailApiError
from app.models.email import Email
from app.models.followup import FollowUp
from app.models.user import User
from app.schemas.reply import (
    ReplyDraftRequest,
    ReplyDraftResponse,
    ReplySendRequest,
    ReplySendResponse,
)
from app.services.gmail_auth_service import get_gmail_service_for_user
from app.services.noise_detection import detect_noise_email
from app.services.reply_generation import ReplyDraftResult, generate_reply_draft
from app.services.thread_state import close_thread_if_work_resolved

router = APIRouter(prefix="/emails", tags=["reply-drafts"])


def _ai_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, (OllamaConnectionError, OllamaModelNotFoundError)):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, OllamaTimeoutError):
        return HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc))
    if isinstance(exc, OllamaInferenceError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Reply draft generation failed.",
    )


def _to_response(result: ReplyDraftResult) -> ReplyDraftResponse:
    return ReplyDraftResponse(
        email_id=result.email_id,
        thread_id=result.thread_id,
        tone=result.tone,
        draft=result.draft,
        context_messages_used=result.context_messages_used,
        regenerated=result.regenerated,
        message=result.message,
    )


def _get_user_email(db: Session, user: User, email_id: int) -> Email:
    email = (
        db.query(Email)
        .filter(Email.id == email_id, Email.user_id == user.id)
        .first()
    )
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found.",
        )
    return email


def _reply_recipient(email: Email) -> str:
    _, address = parseaddr(email.sender or "")
    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send reply because the original sender address is missing.",
        )
    return address


def _mark_thread_followups_resolved(db: Session, user: User, thread_id: str, resolved_at: datetime) -> None:
    records = (
        db.query(FollowUp)
        .filter(
            FollowUp.user_id == user.id,
            FollowUp.thread_id == thread_id,
            FollowUp.status == "open",
            FollowUp.needs_followup.is_(True),
        )
        .all()
    )
    for record in records:
        record.status = "resolved"
        record.needs_followup = False
        record.resolved_at = resolved_at


@router.post("/{email_id}/reply", response_model=ReplyDraftResponse)
async def generate_reply(
    email_id: int,
    payload: ReplyDraftRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReplyDraftResponse:
    if payload.tone.strip().lower() not in REPLY_TONES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tone. Use one of: {', '.join(REPLY_TONES)}",
        )

    email = _get_user_email(db, user, email_id)
    noise = detect_noise_email(email)
    if noise.is_noise:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reply recommendations are disabled for noise emails ({noise.reason}).",
        )

    try:
        result = await generate_reply_draft(
            db,
            user,
            email,
            tone=payload.tone,
            regenerated=False,
        )
    except Exception as exc:
        raise _ai_http_exception(exc) from exc

    return _to_response(result)


@router.post("/{email_id}/reply/regenerate", response_model=ReplyDraftResponse)
async def regenerate_reply(
    email_id: int,
    payload: ReplyDraftRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReplyDraftResponse:
    if payload.tone.strip().lower() not in REPLY_TONES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tone. Use one of: {', '.join(REPLY_TONES)}",
        )

    email = _get_user_email(db, user, email_id)
    noise = detect_noise_email(email)
    if noise.is_noise:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reply recommendations are disabled for noise emails ({noise.reason}).",
        )

    try:
        result = await generate_reply_draft(
            db,
            user,
            email,
            tone=payload.tone,
            regenerated=True,
            previous_draft=payload.previous_draft,
        )
    except Exception as exc:
        raise _ai_http_exception(exc) from exc

    return _to_response(result)


@router.post("/{email_id}/reply/send", response_model=ReplySendResponse)
def send_reply(
    email_id: int,
    payload: ReplySendRequest,
    user: User = Depends(get_current_user_with_token),
    db: Session = Depends(get_db),
) -> ReplySendResponse:
    email = _get_user_email(db, user, email_id)
    noise = detect_noise_email(email)
    if noise.is_noise:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sending replies is disabled for noise emails ({noise.reason}).",
        )

    try:
        print(
            "GMAIL SEND AUTH START:",
            {
                "user_id": user.id,
                "email_id": email.id,
                "refresh_token_present": bool(user.oauth_token.refresh_token) if user.oauth_token else False,
                "access_token_present": bool(user.oauth_token.access_token) if user.oauth_token else False,
                "stored_scopes": get_token_scopes(user.oauth_token) if user.oauth_token else [],
                "required_scopes": GMAIL_SCOPES,
            },
        )
        credentials = refresh_credentials_if_needed(db, user)
        gmail_service = get_gmail_service_for_user(db, user, credentials=credentials)
        print(
            "GMAIL SEND REQUEST:",
            {
                "user_id": user.id,
                "email_id": email.id,
                "thread_id": email.thread_id,
                "recipient_present": bool(_reply_recipient(email)),
                "body_chars": len(payload.body or ""),
                "credential_scopes": list(credentials.scopes or []),
            },
        )
        response = gmail_service.send_reply(
            to=_reply_recipient(email),
            from_email=user.email,
            subject=email.subject or "(No Subject)",
            body=payload.body,
            thread_id=email.thread_id,
        )
        print(
            "GMAIL SEND RESPONSE:",
            {
                "email_id": email.id,
                "gmail_message_id_present": bool(response.get("id")),
                "thread_id_present": bool(response.get("threadId")),
                "label_ids": response.get("labelIds"),
            },
        )
    except OAuthTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except GmailApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send Gmail reply: {exc}",
        ) from exc

    sent_at = datetime.now(timezone.utc)
    sent_message_id = response.get("id")
    sent_thread_id = response.get("threadId") or email.thread_id
    if not sent_message_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gmail send succeeded but returned no message id.",
        )

    email.reply_sent_message_id = sent_message_id
    email.reply_sent_thread_id = sent_thread_id
    email.reply_sent_at = sent_at
    email.reply_sent_body = payload.body.strip()
    _mark_thread_followups_resolved(db, user, email.thread_id, sent_at)
    close_thread_if_work_resolved(
        db,
        user_id=user.id,
        thread_id=email.thread_id,
        reason="reply sent through Gmail",
    )
    db.commit()

    return ReplySendResponse(
        email_id=email.id,
        gmail_message_id=sent_message_id,
        thread_id=sent_thread_id,
        sent_at=sent_at.isoformat(),
        message="Reply sent through Gmail.",
    )
