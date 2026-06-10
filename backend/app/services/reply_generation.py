from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.reply_generation import (
    REPLY_SYSTEM,
    ReplyGenerationContext,
    ReplyTone,
    ThreadMessageSnippet,
    build_reply_prompt,
    clean_email_for_reply,
    clean_reply_draft,
    is_reply_too_short,
    is_repetitive,
    looks_hallucinated,
    MAX_REPLY_OUTPUT_TOKENS,
    normalize_tone,
)
from app.ai.services import generate_text
from app.gmail.parser import parse_gmail_message
from app.models.email import Email
from app.models.user import User
from app.services.gmail_auth_service import get_gmail_service_for_user


@dataclass(frozen=True)
class ReplyDraftResult:
    email_id: int
    thread_id: str
    tone: str
    draft: str
    context_messages_used: int
    regenerated: bool
    message: str


def _email_to_snippet(email: Email) -> ThreadMessageSnippet:
    body = (email.body_cleaned or "").strip()
    return ThreadMessageSnippet(
        sender=email.sender or "Unknown Sender",
        subject=email.subject or "(No Subject)",
        body=clean_email_for_reply(body) or "(Empty body)",
    )


def _message_dict_to_snippet(message: dict) -> ThreadMessageSnippet:
    parsed = parse_gmail_message(message)
    body = clean_email_for_reply(parsed.body_cleaned or parsed.body_raw)
    return ThreadMessageSnippet(
        sender=parsed.sender,
        subject=parsed.subject,
        body=body,
    )


def get_prior_messages_from_db(
    db: Session,
    email: Email,
    *,
    limit: int = 1,
) -> list[ThreadMessageSnippet]:
    rows = (
        db.query(Email)
        .filter(
            Email.user_id == email.user_id,
            Email.thread_id == email.thread_id,
            Email.id != email.id,
        )
        .order_by(Email.received_at.desc())
        .limit(limit)
        .all()
    )
    return [_email_to_snippet(row) for row in reversed(rows)]


def fetch_prior_messages_from_gmail(
    db: Session,
    user: User,
    email: Email,
    *,
    limit: int = 1,
) -> list[ThreadMessageSnippet]:
    if user.oauth_token is None:
        return []

    gmail = get_gmail_service_for_user(db, user)
    thread = gmail.get_thread(email.thread_id, format="full")
    messages = thread.get("messages") or []
    if not messages:
        return []

    sorted_messages = sorted(
        messages,
        key=lambda item: int(item.get("internalDate") or 0),
    )

    prior: list[ThreadMessageSnippet] = []
    for message in sorted_messages:
        message_id = message.get("id")
        if message_id == email.gmail_message_id:
            continue
        prior.append(_message_dict_to_snippet(message))

    return prior[-limit:]


def build_reply_context(
    db: Session,
    email: Email,
    user: User,
    tone: ReplyTone,
) -> ReplyGenerationContext:
    current = _email_to_snippet(email)
    prior = get_prior_messages_from_db(db, email, limit=1)

    if not prior and user.oauth_token is not None:
        try:
            gmail_prior = fetch_prior_messages_from_gmail(db, user, email, limit=1)
            if gmail_prior:
                prior = gmail_prior
        except Exception:
            pass

    return ReplyGenerationContext(
        current=current,
        prior_messages=prior,
        tone=tone,
    )


async def _generate_draft_text(
    context: ReplyGenerationContext,
    *,
    strict: bool = False,
) -> str:
    prompt = build_reply_prompt(context)
    system = REPLY_SYSTEM
    if strict:
        system += " Be brief. No attachments or meetings unless explicitly in the email."

    raw = await generate_text(
        prompt,
        system=system,
        temperature=0.3 if not strict else 0.15,
        max_tokens=MAX_REPLY_OUTPUT_TOKENS,
    )
    return clean_reply_draft(raw)


async def generate_reply_draft(
    db: Session,
    user: User,
    email: Email,
    *,
    tone: str | None = "neutral",
    regenerated: bool = False,
    previous_draft: str | None = None,
) -> ReplyDraftResult:
    normalized_tone = normalize_tone(tone)

    body = (email.body_cleaned or "").strip()
    if not body:
        raise ValueError("Email has no cleaned content. Process the email before generating a reply.")

    context = build_reply_context(db, email, user, normalized_tone)
    context_messages_used = 1 + len(context.prior_messages)
    if not context.current.body or context.current.body == "(Empty body)":
        raise ValueError("Email has no usable content after cleaning.")

    draft = await _generate_draft_text(context)
    source_body = context.current.body

    needs_retry = (
        is_reply_too_short(draft)
        or looks_hallucinated(draft, source_body)
        or is_repetitive(draft, previous_draft)
    )

    if needs_retry:
        draft = await _generate_draft_text(context, strict=True)

    if is_reply_too_short(draft):
        raise ValueError("Failed to generate a valid reply draft.")

    return ReplyDraftResult(
        email_id=email.id,
        thread_id=email.thread_id,
        tone=normalized_tone,
        draft=draft,
        context_messages_used=context_messages_used,
        regenerated=regenerated,
        message="Reply draft generated successfully.",
    )
