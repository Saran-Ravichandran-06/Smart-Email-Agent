from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parseaddr
import re
from time import perf_counter

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.email import Email
from app.models.followup import FollowUp
from app.models.user import User
from app.services.noise_detection import detect_noise_email
from app.services.thread_state import close_thread_if_work_resolved, detect_email_intent

FOLLOWUP_STATUS_OPEN = "open"
FOLLOWUP_STATUS_RESOLVED = "resolved"

REASON_STALE_INCOMING = "stale_incoming_no_reply"
REASON_PRIORITY_STALE = "priority_thread_stale"
REASON_SENT_AWAITING = "sent_awaiting_response"
REASON_RESPONSE_REQUIRED = "response_required"

SKIP_PRIORITIES = frozenset({"noise"})

REQUEST_PATTERNS = (
    r"\bcan you\b",
    r"\bcould you\b",
    r"\bwould you\b",
    r"\bplease\b",
    r"\bkindly\b",
    r"\blet me know\b",
    r"\bconfirm\b",
    r"\bapprove\b",
    r"\bapproval\b",
    r"\breview\b",
    r"\bfeedback\b",
    r"\bshare\b",
    r"\bsend\b",
    r"\bsubmit\b",
    r"\bcomplete\b",
    r"\bprovide\b",
    r"\brespond\b",
    r"\breply\b",
    r"\bquestion\b",
    r"\brequest\b",
    r"\baction required\b",
    r"\brequires? (your )?(response|approval|review|feedback|input|action)\b",
    r"\?",
)
@dataclass(frozen=True)
class FollowUpCandidate:
    thread_id: str
    last_activity: datetime
    reason: str
    latest_email_id: int
    priority_snapshot: str | None
    subject: str
    latest_sender: str


@dataclass(frozen=True)
class FollowUpScanResult:
    scanned_threads: int
    created: int
    updated: int
    skipped: int
    cleared: int
    candidates: list[int]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _hours_since(timestamp: datetime, now: datetime) -> float:
    ts = _ensure_aware(timestamp)
    return (now - ts).total_seconds() / 3600


def is_sender_user(sender: str, user_email: str) -> bool:
    _, address = parseaddr(sender or "")
    return address.lower().strip() == user_email.lower().strip()


def _address_from_header(value: str | None) -> str:
    _, address = parseaddr(value or "")
    return address.lower().strip()


def _local_part(address: str) -> str:
    return address.split("@", 1)[0].lower() if "@" in address else address.lower()


def is_automated_or_noise_email(email: Email) -> bool:
    noise = detect_noise_email(email)
    if noise.is_noise:
        print("FOLLOWUP EVALUATION SKIP CHECK:", {"email_id": email.id, "reason": noise.reason})
        return True
    return False


def requires_user_response(email: Email) -> tuple[bool, str | None]:
    text = " ".join(
        part.strip()
        for part in (email.subject or "", email.body_cleaned or "", email.body or "")
        if part and part.strip()
    ).lower()
    for pattern in REQUEST_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True, pattern
    return False, None


def get_thread_emails(db: Session, user_id: int) -> dict[str, list[Email]]:
    emails = (
        db.query(Email)
        .filter(Email.user_id == user_id)
        .order_by(Email.received_at.asc())
        .all()
    )
    threads: dict[str, list[Email]] = {}
    for email in emails:
        threads.setdefault(email.thread_id, []).append(email)
    return threads


def evaluate_thread(
    emails: list[Email],
    *,
    user_email: str,
    now: datetime | None = None,
) -> FollowUpCandidate | None:
    if not emails:
        return None

    now = now or _utc_now()
    sorted_emails = sorted(emails, key=lambda e: _ensure_aware(e.received_at))
    latest = sorted_emails[-1]

    last_activity = _ensure_aware(latest.received_at)
    hours_idle = _hours_since(last_activity, now)
    priority = (latest.priority or "low").lower()
    outgoing = is_sender_user(latest.sender, user_email)
    detected_intent = detect_email_intent(latest)
    requires_response, response_pattern = requires_user_response(latest)
    print(
        "FOLLOWUP EVALUATION START:",
        {
            "thread_id": latest.thread_id,
            "latest_email_id": latest.id,
            "latest_subject": latest.subject,
            "priority": latest.priority,
            "hours_idle": round(hours_idle, 2),
            "outgoing": outgoing,
            "message_count": len(sorted_emails),
            "requires_response": requires_response,
            "response_pattern": response_pattern,
            "detected_intent": detected_intent,
        },
    )

    if detected_intent == "acknowledgement":
        print("FOLLOWUP EVALUATION RESULT:", {"thread_id": latest.thread_id, "candidate": False, "reason": "acknowledgement"})
        return None

    if is_automated_or_noise_email(latest):
        print("FOLLOWUP EVALUATION RESULT:", {"thread_id": latest.thread_id, "candidate": False, "reason": "automated_or_noise"})
        return None

    if priority in SKIP_PRIORITIES and not outgoing:
        print("FOLLOWUP EVALUATION RESULT:", {"thread_id": latest.thread_id, "candidate": False, "reason": "noise priority"})
        return None

    if outgoing:
        print("FOLLOWUP EVALUATION RESULT:", {"thread_id": latest.thread_id, "candidate": False, "reason": "latest message outgoing"})
        return None

    if requires_response:
        print("FOLLOWUP EVALUATION RESULT:", {"thread_id": latest.thread_id, "candidate": True, "reason": REASON_RESPONSE_REQUIRED})
        return FollowUpCandidate(
            thread_id=latest.thread_id,
            last_activity=last_activity,
            reason=REASON_RESPONSE_REQUIRED,
            latest_email_id=latest.id,
            priority_snapshot=latest.priority,
            subject=latest.subject,
            latest_sender=latest.sender,
        )

    print("FOLLOWUP EVALUATION RESULT:", {"thread_id": latest.thread_id, "candidate": False, "reason": "no response required"})
    return None


def get_open_followup(db: Session, user_id: int, thread_id: str) -> FollowUp | None:
    return (
        db.query(FollowUp)
        .filter(
            FollowUp.user_id == user_id,
            FollowUp.thread_id == thread_id,
            FollowUp.status == FOLLOWUP_STATUS_OPEN,
        )
        .first()
    )


def upsert_followup_candidate(
    db: Session,
    user_id: int,
    candidate: FollowUpCandidate,
) -> tuple[FollowUp, bool]:
    existing = get_open_followup(db, user_id, candidate.thread_id)

    if existing:
        print(
            "FOLLOWUP DB UPDATE:",
            {
                "followup_id": existing.id,
                "thread_id": candidate.thread_id,
                "latest_email_id": candidate.latest_email_id,
                "reason": candidate.reason,
            },
        )
        existing.last_activity = candidate.last_activity
        existing.needs_followup = True
        existing.reason = candidate.reason
        existing.latest_email_id = candidate.latest_email_id
        existing.priority_snapshot = candidate.priority_snapshot
        return existing, False

    record = FollowUp(
        user_id=user_id,
        thread_id=candidate.thread_id,
        last_activity=candidate.last_activity,
        needs_followup=True,
        reason=candidate.reason,
        status=FOLLOWUP_STATUS_OPEN,
        latest_email_id=candidate.latest_email_id,
        priority_snapshot=candidate.priority_snapshot,
    )
    db.add(record)
    print(
        "FOLLOWUP DB INSERT:",
        {
            "thread_id": candidate.thread_id,
            "latest_email_id": candidate.latest_email_id,
            "reason": candidate.reason,
            "priority_snapshot": candidate.priority_snapshot,
        },
    )
    return record, True


def clear_stale_open_followup(
    db: Session,
    followup: FollowUp,
) -> None:
    followup.needs_followup = False


def scan_followups_for_user(
    db: Session,
    user: User,
    *,
    thread_ids: set[str] | None = None,
) -> FollowUpScanResult:
    started = perf_counter()
    threads = get_thread_emails(db, user.id)
    if thread_ids is not None:
        threads = {thread_id: emails for thread_id, emails in threads.items() if thread_id in thread_ids}
    print(
        "FOLLOWUP SCAN START:",
        {
            "user_id": user.id,
            "thread_count": len(threads),
            "thread_ids": list(threads.keys()),
            "targeted": thread_ids is not None,
        },
    )
    now = _utc_now()

    created = 0
    updated = 0
    skipped = 0
    cleared = 0
    candidate_ids: list[int] = []

    for thread_id, emails in threads.items():
        candidate = evaluate_thread(emails, user_email=user.email, now=now)
        if candidate is None:
            existing = get_open_followup(db, user.id, thread_id)
            if existing and existing.needs_followup:
                clear_stale_open_followup(db, existing)
                cleared += 1
            else:
                skipped += 1
            continue

        record, is_new = upsert_followup_candidate(db, user.id, candidate)
        if is_new:
            created += 1
        else:
            updated += 1
        for email in emails:
            email.followup_evaluated_at = now

    for emails in threads.values():
        for email in emails:
            if email.followup_evaluated_at is None:
                email.followup_evaluated_at = now

    db.commit()
    print(
        "FOLLOWUP SCAN COMMIT:",
        {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "cleared": cleared,
            "duration_ms": round((perf_counter() - started) * 1000, 2),
        },
    )

    open_records = list_open_followups(db, user.id)
    candidate_ids = [record.id for record in open_records]

    return FollowUpScanResult(
        scanned_threads=len(threads),
        created=created,
        updated=updated,
        skipped=skipped,
        cleared=cleared,
        candidates=candidate_ids,
    )


def list_open_followups(db: Session, user_id: int) -> list[FollowUp]:
    return (
        db.query(FollowUp)
        .filter(
            FollowUp.user_id == user_id,
            FollowUp.status == FOLLOWUP_STATUS_OPEN,
            FollowUp.needs_followup.is_(True),
        )
        .order_by(FollowUp.last_activity.asc())
        .all()
    )


def mark_followup_resolved(db: Session, followup: FollowUp) -> FollowUp:
    followup.status = FOLLOWUP_STATUS_RESOLVED
    followup.needs_followup = False
    followup.resolved_at = _utc_now()
    close_thread_if_work_resolved(
        db,
        user_id=followup.user_id,
        thread_id=followup.thread_id,
        reason="follow-up resolved",
    )
    db.commit()
    db.refresh(followup)
    return followup


def get_followup_for_user(
    db: Session,
    user_id: int,
    followup_id: int,
) -> FollowUp | None:
    return (
        db.query(FollowUp)
        .filter(FollowUp.id == followup_id, FollowUp.user_id == user_id)
        .first()
    )
