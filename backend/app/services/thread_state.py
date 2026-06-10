import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.email import Email
from app.models.followup import FollowUp
from app.models.task import Task
from app.models.thread_state import ThreadState

THREAD_STATUS_OPEN = "open"
THREAD_STATUS_RESOLVED = "resolved"

ACK_ONLY_PATTERNS = (
    r"^\s*(thanks|thank you|received|noted|looks good|approved|great work|appreciated)[.!]?\s*$",
    r"^\s*(thanks|thank you)\s+(for|so much|very much|again).*?[.!]?\s*$",
)

ACK_PHRASES = (
    "thanks",
    "thank you",
    "everything looks good",
    "looks good",
    "approved",
    "great work",
    "appreciated",
    "appreciate the quick turnaround",
    "received",
    "noted",
    "sounds good",
    "perfect",
)

REQUEST_PHRASES = (
    "please",
    "can you",
    "could you",
    "would you",
    "submit",
    "complete",
    "review",
    "approve",
    "provide",
    "feedback",
    "confirm",
    "action required",
)


@dataclass(frozen=True)
class ThreadTaskDecision:
    should_create: bool
    reason: str
    thread_state: str
    existing_task_count: int


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_thread_state(db: Session, user_id: int, thread_id: str) -> ThreadState | None:
    return (
        db.query(ThreadState)
        .filter(ThreadState.user_id == user_id, ThreadState.thread_id == thread_id)
        .first()
    )


def upsert_thread_state(
    db: Session,
    *,
    user_id: int,
    thread_id: str,
    status: str,
    reason: str | None = None,
) -> ThreadState:
    state = get_thread_state(db, user_id, thread_id)
    if state is None:
        state = ThreadState(user_id=user_id, thread_id=thread_id)
        db.add(state)
    state.status = status
    if status == THREAD_STATUS_RESOLVED:
        state.resolved_at = state.resolved_at or utc_now()
        state.resolution_reason = reason
    else:
        state.resolved_at = None
        state.resolution_reason = reason
    return state


def thread_task_count(db: Session, user_id: int, thread_id: str) -> int:
    return (
        db.query(Task)
        .join(Email, Task.email_id == Email.id)
        .filter(Email.user_id == user_id, Email.thread_id == thread_id)
        .count()
    )


def thread_pending_task_count(db: Session, user_id: int, thread_id: str) -> int:
    return (
        db.query(Task)
        .join(Email, Task.email_id == Email.id)
        .filter(
            Email.user_id == user_id,
            Email.thread_id == thread_id,
            Task.status != "completed",
        )
        .count()
    )


def thread_has_sent_reply(db: Session, user_id: int, thread_id: str) -> bool:
    return (
        db.query(Email.id)
        .filter(
            Email.user_id == user_id,
            Email.thread_id == thread_id,
            Email.reply_sent_at.isnot(None),
        )
        .first()
        is not None
    )


def thread_has_resolved_followup(db: Session, user_id: int, thread_id: str) -> bool:
    return (
        db.query(FollowUp.id)
        .filter(
            FollowUp.user_id == user_id,
            FollowUp.thread_id == thread_id,
            FollowUp.status == "resolved",
        )
        .first()
        is not None
    )


def close_thread_if_work_resolved(
    db: Session,
    *,
    user_id: int,
    thread_id: str,
    reason: str,
) -> ThreadState | None:
    existing_task_count = thread_task_count(db, user_id, thread_id)
    pending_task_count = thread_pending_task_count(db, user_id, thread_id)
    followup_done = thread_has_sent_reply(db, user_id, thread_id) or thread_has_resolved_followup(
        db, user_id, thread_id
    )
    print(
        "THREAD STATE RESOLUTION CHECK:",
        {
            "thread_id": thread_id,
            "existing_task_count": existing_task_count,
            "pending_task_count": pending_task_count,
            "followup_done": followup_done,
            "reason": reason,
        },
    )
    if existing_task_count > 0 and pending_task_count == 0 and followup_done:
        state = upsert_thread_state(
            db,
            user_id=user_id,
            thread_id=thread_id,
            status=THREAD_STATUS_RESOLVED,
            reason=reason,
        )
        print(
            "THREAD STATE CLOSED:",
            {
                "thread_id": thread_id,
                "thread_state": state.status,
                "existing_task_count": existing_task_count,
                "reason_for_decision": reason,
            },
        )
        return state
    return None


def reconcile_resolved_threads_for_user(db: Session, user_id: int) -> int:
    thread_ids = {
        row[0]
        for row in (
            db.query(Email.thread_id)
            .filter(Email.user_id == user_id)
            .distinct()
            .all()
        )
    }
    closed = 0
    for thread_id in thread_ids:
        state = close_thread_if_work_resolved(
            db,
            user_id=user_id,
            thread_id=thread_id,
            reason="post-sync reconciliation",
        )
        if state is not None:
            closed += 1
    if closed:
        db.commit()
    print(
        "THREAD STATE RECONCILIATION:",
        {
            "user_id": user_id,
            "threads_checked": len(thread_ids),
            "threads_closed": closed,
        },
    )
    return closed


def is_acknowledgement_only_email(email: Email) -> bool:
    return detect_email_intent(email) == "acknowledgement"


def detect_email_intent(email: Email) -> str:
    text = (email.body_cleaned or email.body or "").strip()
    if not text:
        text = (email.subject or "").strip()
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    if not normalized:
        return "empty"
    has_request = any(
        re.search(rf"\b{re.escape(phrase)}\b", normalized)
        for phrase in REQUEST_PHRASES
    ) or "?" in normalized
    if len(normalized) <= 220:
        ack_hits = sum(1 for phrase in ACK_PHRASES if phrase in normalized)
        if ack_hits > 0 and not has_request:
            return "acknowledgement"
    if any(re.match(pattern, normalized, flags=re.IGNORECASE) for pattern in ACK_ONLY_PATTERNS):
        return "acknowledgement"
    if has_request:
        return "action_request"
    return "informational"


def email_has_actionable_request(email: Email) -> bool:
    text = " ".join(
        part.strip()
        for part in (email.subject or "", email.body_cleaned or "", email.body or "")
        if part and part.strip()
    ).lower()
    request_patterns = tuple(rf"\b{re.escape(phrase)}\b" for phrase in REQUEST_PHRASES) + (r"\?",)
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in request_patterns)


def decide_task_creation_for_email(db: Session, email: Email) -> ThreadTaskDecision:
    state = get_thread_state(db, email.user_id, email.thread_id)
    thread_state = state.status if state else THREAD_STATUS_OPEN
    existing_task_count = thread_task_count(db, email.user_id, email.thread_id)

    if is_acknowledgement_only_email(email):
        return ThreadTaskDecision(
            should_create=False,
            reason="acknowledgement-only email",
            thread_state=thread_state,
            existing_task_count=existing_task_count,
        )

    if thread_state == THREAD_STATUS_RESOLVED:
        if email_has_actionable_request(email):
            upsert_thread_state(
                db,
                user_id=email.user_id,
                thread_id=email.thread_id,
                status=THREAD_STATUS_OPEN,
                reason="new actionable request in resolved thread",
            )
            return ThreadTaskDecision(
                should_create=True,
                reason="new actionable request reopened resolved thread",
                thread_state=THREAD_STATUS_OPEN,
                existing_task_count=existing_task_count,
            )
        return ThreadTaskDecision(
            should_create=False,
            reason="resolved thread with no new actionable request",
            thread_state=thread_state,
            existing_task_count=existing_task_count,
        )

    return ThreadTaskDecision(
        should_create=True,
        reason="open thread",
        thread_state=thread_state,
        existing_task_count=existing_task_count,
    )
