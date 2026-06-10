from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.email import Email
from app.processing.pipeline import process_raw_email_content
from app.processing.types import ProcessedEmailContent


@dataclass(frozen=True)
class EmailProcessResult:
    email_id: int
    gmail_message_id: str
    processed: bool
    message: str


@dataclass(frozen=True)
class BatchProcessResult:
    processed: int
    skipped: int
    failed: int
    results: list[EmailProcessResult]


def _ensure_body_raw(email: Email) -> str:
    if email.body_raw and email.body_raw.strip():
        return email.body_raw
    return email.body or ""


def apply_processed_content(email: Email, processed: ProcessedEmailContent) -> Email:
    """Persist cleaned output without overwriting preserved raw content."""
    raw = processed.body_raw.strip() or _ensure_body_raw(email)

    if not email.body_raw:
        email.body_raw = raw

    email.body_cleaned = processed.body_cleaned
    email.recipient = processed.metadata.recipient or email.recipient
    email.sender = processed.metadata.sender or email.sender
    email.subject = processed.metadata.subject or email.subject
    email.processed_at = datetime.now(timezone.utc)
    return email


def process_email_record(db: Session, email: Email) -> EmailProcessResult:
    try:
        raw = _ensure_body_raw(email)
        if not raw.strip():
            return EmailProcessResult(
                email_id=email.id,
                gmail_message_id=email.gmail_message_id,
                processed=False,
                message="Skipped: empty email body.",
            )

        processed = process_raw_email_content(
            gmail_message_id=email.gmail_message_id,
            thread_id=email.thread_id,
            sender=email.sender,
            recipient=email.recipient,
            subject=email.subject,
            timestamp=email.received_at,
            body_raw=raw,
        )
        apply_processed_content(email, processed)

        return EmailProcessResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            processed=True,
            message="Email processed successfully.",
        )
    except Exception as exc:
        return EmailProcessResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            processed=False,
            message=f"Processing failed: {exc}",
        )


def process_single_email(db: Session, email: Email, *, commit: bool = True) -> EmailProcessResult:
    result = process_email_record(db, email)
    if result.processed and commit:
        db.commit()
        db.refresh(email)
    return result


def get_unprocessed_emails(db: Session, user_id: int) -> list[Email]:
    return (
        db.query(Email)
        .filter(Email.user_id == user_id, Email.processed_at.is_(None))
        .order_by(Email.received_at.desc())
        .all()
    )


def process_email_batch(
    db: Session,
    emails: list[Email],
    *,
    commit: bool = True,
) -> BatchProcessResult:
    processed = 0
    skipped = 0
    failed = 0
    results: list[EmailProcessResult] = []

    for email in emails:
        result = process_email_record(db, email)
        results.append(result)
        if result.processed:
            processed += 1
        elif "empty" in result.message.lower():
            skipped += 1
        else:
            failed += 1

    if processed and commit:
        db.commit()

    return BatchProcessResult(
        processed=processed,
        skipped=skipped,
        failed=failed,
        results=results,
    )


def process_unprocessed_for_user(db: Session, user_id: int) -> BatchProcessResult:
    emails = get_unprocessed_emails(db, user_id)
    return process_email_batch(db, emails)
