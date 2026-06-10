import logging
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.gmail.parser import ParsedGmailMessage, parse_gmail_message
from app.gmail.service import GmailService
from app.models.email import Email
from app.models.followup import FollowUp
from app.models.user import User

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailSyncResult:
    synced: int
    skipped: int
    total_fetched: int
    synced_email_ids: list[int]


def get_existing_gmail_message_ids(db: Session, user_id: int) -> set[str]:
    rows = (
        db.query(Email.gmail_message_id)
        .filter(Email.user_id == user_id)
        .all()
    )
    return {row[0] for row in rows}


def save_parsed_email(db: Session, user_id: int, parsed: ParsedGmailMessage) -> Email:
    now = datetime.now(timezone.utc)
    email = Email(
        gmail_message_id=parsed.gmail_message_id,
        gmail_history_id=parsed.gmail_history_id,
        thread_id=parsed.thread_id,
        sender=parsed.sender,
        recipient=parsed.recipient,
        cc=parsed.cc,
        subject=parsed.subject,
        body=parsed.body_cleaned or parsed.body_raw,
        body_raw=parsed.body_raw,
        body_cleaned=parsed.body_cleaned,
        processed_at=now if parsed.body_cleaned else None,
        gmail_synced_at=now,
        gmail_deleted_at=None,
        label_ids=parsed.label_ids,
        received_at=parsed.received_at,
        user_id=user_id,
        priority=None,
        summary=None,
    )
    db.add(email)
    return email


def update_existing_email_from_gmail(email: Email, parsed: ParsedGmailMessage) -> None:
    email.gmail_history_id = parsed.gmail_history_id
    email.thread_id = parsed.thread_id or email.thread_id
    email.sender = parsed.sender or email.sender
    email.recipient = parsed.recipient
    email.cc = parsed.cc
    email.subject = parsed.subject or email.subject
    email.label_ids = parsed.label_ids
    email.received_at = parsed.received_at
    email.gmail_synced_at = datetime.now(timezone.utc)
    email.gmail_deleted_at = None

    if parsed.body_cleaned:
        email.body = parsed.body_cleaned
        email.body_raw = parsed.body_raw
        email.body_cleaned = parsed.body_cleaned
        email.processed_at = email.processed_at or datetime.now(timezone.utc)


def sync_user_inbox(
    db: Session,
    user: User,
    gmail_service: GmailService,
    *,
    max_messages: int = 50,
) -> EmailSyncResult:
    try:
        print("EMAIL SYNC STAGE [load existing Gmail message ids]: start", {"user_id": user.id})
        existing_ids = get_existing_gmail_message_ids(db, user.id)
        print(
            "EMAIL SYNC STAGE [load existing Gmail message ids]: success",
            {"existing_count": len(existing_ids)},
        )
    except Exception as exc:
        _log_sync_stage_error("load existing Gmail message ids", exc)
        raise

    synced = 0
    skipped = 0
    total_fetched = 0
    synced_email_ids: list[int] = []

    try:
        print("EMAIL SYNC STAGE [fetch Gmail message list]: start", {"max_messages": max_messages})
        message_ids = list(gmail_service.iter_inbox_message_ids(max_messages=max_messages))
        total_fetched = len(message_ids)
        print(
            "EMAIL SYNC STAGE [fetch Gmail message list]: success",
            {"total_fetched": total_fetched},
        )
    except Exception as exc:
        _log_sync_stage_error("fetch Gmail message list", exc)
        raise

    existing_by_id = {
        email.gmail_message_id: email
        for email in db.query(Email).filter(Email.user_id == user.id).all()
    }
    current_id_set = set(message_ids)

    for message_id in message_ids:
        print("EMAIL SYNC MESSAGE:", {"message_id": _mask_message_id(message_id)})
        try:
            print(
                "EMAIL SYNC STAGE [fetch Gmail message details]: start",
                {"message_id": _mask_message_id(message_id)},
            )
            message = gmail_service.get_message(message_id, format="full")
            print(
                "EMAIL SYNC STAGE [fetch Gmail message details]: success",
                {
                    "message_id": _mask_message_id(message.get("id")),
                    "thread_id": _mask_message_id(message.get("threadId")),
                    "label_count": len(message.get("labelIds") or []),
                },
            )
        except Exception as exc:
            _log_sync_stage_error("fetch Gmail message details", exc, message_id=message_id)
            raise

        try:
            print(
                "EMAIL SYNC STAGE [parse Gmail message]: start",
                {"message_id": _mask_message_id(message_id)},
            )
            parsed = parse_gmail_message(message)
            print(
                "EMAIL SYNC STAGE [parse Gmail message]: success",
                {
                    "gmail_message_id": _mask_message_id(parsed.gmail_message_id),
                    "thread_id": _mask_message_id(parsed.thread_id),
                    "sender_present": bool(parsed.sender),
                    "subject_present": bool(parsed.subject),
                    "body_raw_length": len(parsed.body_raw or ""),
                    "body_cleaned_length": len(parsed.body_cleaned or ""),
                },
            )
        except Exception as exc:
            _log_sync_stage_error("parse Gmail message", exc, message_id=message_id)
            raise

        if not parsed.gmail_message_id:
            skipped += 1
            print("EMAIL SYNC STAGE [parsed message validation]: skipped missing gmail_message_id")
            continue

        try:
            existing_email = existing_by_id.get(parsed.gmail_message_id)
            if existing_email is not None:
                print(
                    "EMAIL SYNC STAGE [update existing email metadata]: start",
                    {"email_id": existing_email.id, "gmail_message_id": _mask_message_id(parsed.gmail_message_id)},
                )
                update_existing_email_from_gmail(existing_email, parsed)
                skipped += 1
                print(
                    "EMAIL SYNC STAGE [update existing email metadata]: success",
                    {
                        "email_id": existing_email.id,
                        "label_ids": parsed.label_ids,
                        "history_id": parsed.gmail_history_id,
                    },
                )
                continue

            print(
                "EMAIL SYNC STAGE [save email to database]: start",
                {"gmail_message_id": _mask_message_id(parsed.gmail_message_id), "user_id": user.id},
            )
            email = save_parsed_email(db, user.id, parsed)
            db.flush()
            existing_ids.add(parsed.gmail_message_id)
            synced += 1
            if email.id:
                synced_email_ids.append(email.id)
            print(
                "EMAIL SYNC STAGE [save email to database]: success",
                {"synced_count": synced},
            )
        except Exception as exc:
            _log_sync_stage_error("save emails to database", exc, message_id=message_id)
            raise

    removed_count = mark_missing_inbox_messages(db, user.id, current_id_set)

    if synced or skipped or removed_count:
        try:
            print(
                "EMAIL SYNC STAGE [commit transaction]: start",
                {"synced": synced, "metadata_updates": skipped, "marked_removed": removed_count},
            )
            db.commit()
            print(
                "EMAIL SYNC STAGE [commit transaction]: success",
                {"synced": synced, "metadata_updates": skipped, "marked_removed": removed_count},
            )
        except Exception as exc:
            _log_sync_stage_error("commit transaction", exc)
            raise
    else:
        print("EMAIL SYNC STAGE [commit transaction]: skipped", {"synced": synced})

    return EmailSyncResult(
        synced=synced,
        skipped=skipped,
        total_fetched=total_fetched,
        synced_email_ids=synced_email_ids,
    )


def mark_missing_inbox_messages(db: Session, user_id: int, current_gmail_ids: set[str]) -> int:
    now = datetime.now(timezone.utc)
    candidates = (
        db.query(Email)
        .filter(
            Email.user_id == user_id,
            Email.gmail_deleted_at.is_(None),
            Email.label_ids.contains("INBOX"),
        )
        .all()
    )
    removed = 0
    for email in candidates:
        if email.gmail_message_id not in current_gmail_ids:
            email.gmail_deleted_at = now
            open_followups = (
                db.query(FollowUp)
                .filter(
                    FollowUp.user_id == user_id,
                    FollowUp.thread_id == email.thread_id,
                    FollowUp.status == "open",
                    FollowUp.needs_followup.is_(True),
                )
                .all()
            )
            for followup in open_followups:
                followup.needs_followup = False
                followup.status = "resolved"
                followup.resolved_at = now
            removed += 1
            print(
                "EMAIL SYNC STAGE [mark missing Gmail message]:",
                {"email_id": email.id, "gmail_message_id": _mask_message_id(email.gmail_message_id)},
            )
    return removed


def _mask_message_id(message_id: str | None) -> str | None:
    if not message_id:
        return None
    if len(message_id) <= 8:
        return f"{message_id[:3]}..."
    return f"{message_id[:4]}...{message_id[-4:]}"


def _log_sync_stage_error(
    stage: str,
    exc: Exception,
    *,
    message_id: str | None = None,
) -> None:
    context = {"message_id": _mask_message_id(message_id)} if message_id else {}
    print(f"EMAIL SYNC STAGE ERROR [{stage}]:", exc.__class__.__name__, str(exc), context)
    traceback.print_exc()
    logger.exception("Email sync failed during %s context=%s", stage, context)
