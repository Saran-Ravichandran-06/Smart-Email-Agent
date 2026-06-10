import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from time import perf_counter

from sqlalchemy.orm import Session

from app.ai.classification import (
    CLASSIFICATION_SCHEMA_HINT,
    CLASSIFICATION_SYSTEM,
    EmailPriorityInput,
    PriorityClassificationResult,
    PriorityLevel,
    build_classification_prompt,
    normalize_priority,
)
from app.ai.exceptions import AIResponseParseError
from app.ai.parser import parse_structured_response
from app.ai.services import generate_structured, generate_text
from app.models.email import Email
from app.models.followup import FollowUp
from app.models.task import Task
from app.services.noise_detection import detect_noise_email
from app.services.thread_state import close_thread_if_work_resolved, detect_email_intent


@dataclass(frozen=True)
class ClassificationResult:
    email_id: int
    gmail_message_id: str
    classified: bool
    priority: str | None
    message: str


@dataclass(frozen=True)
class BatchClassificationResult:
    classified: int
    skipped: int
    failed: int
    results: list[ClassificationResult]


@dataclass(frozen=True)
class DeadlinePriorityDecision:
    priority: PriorityLevel
    detected_deadline: str | None
    due_date: date | None
    days_until_due: int | None
    reason: str


URGENT_KEYWORD_RE = re.compile(
    r"\b(asap|urgent|immediately|critical|right away|as soon as possible)\b",
    flags=re.IGNORECASE,
)
WEEKDAY_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
MONTH_TO_NUMBER = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def extract_classification_input(email: Email) -> EmailPriorityInput | None:
    body = (email.body_cleaned or "").strip()
    if not body:
        return None

    return EmailPriorityInput(
        sender=(email.sender or "Unknown Sender").strip()[:255],
        subject=(email.subject or "(No Subject)").strip()[:512],
        body_cleaned=body,
    )


def current_system_date() -> date:
    return datetime.now().date()


def _next_weekday(today: date, weekday_index: int) -> date:
    days_ahead = (weekday_index - today.weekday()) % 7
    return today + timedelta(days=days_ahead)


def _end_of_week(today: date) -> date:
    friday_index = WEEKDAY_TO_INDEX["friday"]
    return today + timedelta(days=friday_index - today.weekday())


def detect_deadline(text: str, *, today: date | None = None) -> tuple[str | None, date | None]:
    today = today or current_system_date()
    lowered = text.lower()

    if re.search(r"\b(today|end of day|eod)\b", lowered):
        return "today", today
    if re.search(r"\b(tomorrow|next day)\b", lowered):
        return "tomorrow", today + timedelta(days=1)
    if re.search(r"\b(end of week|end-of-week|eow)\b", lowered):
        return "end of week", _end_of_week(today)
    if re.search(r"\bnext week\b", lowered):
        days_until_next_monday = (7 - today.weekday()) % 7
        if days_until_next_monday == 0:
            days_until_next_monday = 7
        return "next week", today + timedelta(days=days_until_next_monday)

    for weekday, index in WEEKDAY_TO_INDEX.items():
        if re.search(rf"\b(?:by|before|on|due\s+)?{weekday}\b", lowered):
            return weekday, _next_weekday(today, index)

    iso_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    if iso_match:
        year, month, day = (int(part) for part in iso_match.groups())
        try:
            due = date(year, month, day)
            return iso_match.group(0), due
        except ValueError:
            pass

    month_match = re.search(
        r"\b("
        + "|".join(MONTH_TO_NUMBER)
        + r")\s+(\d{1,2})(?:,\s*(\d{4}))?\b",
        lowered,
        flags=re.IGNORECASE,
    )
    if month_match:
        month_text, day_text, year_text = month_match.groups()
        year = int(year_text) if year_text else today.year
        month = MONTH_TO_NUMBER[month_text.lower()]
        day = int(day_text)
        try:
            due = date(year, month, day)
            if not year_text and due < today:
                due = date(today.year + 1, month, day)
            return month_match.group(0), due
        except ValueError:
            pass

    return None, None


def deterministic_priority_decision(
    email: Email,
    *,
    detected_intent: str,
    today: date | None = None,
) -> DeadlinePriorityDecision | None:
    today = today or current_system_date()
    text = " ".join(
        part.strip()
        for part in (email.subject or "", email.body_cleaned or "", email.body or "")
        if part and part.strip()
    )

    if URGENT_KEYWORD_RE.search(text):
        return DeadlinePriorityDecision(
            priority="urgent",
            detected_deadline=None,
            due_date=None,
            days_until_due=None,
            reason="urgent keyword present",
        )

    detected_deadline, due_date = detect_deadline(text, today=today)
    if due_date is not None:
        days_until_due = (due_date - today).days
        if days_until_due <= 1:
            priority: PriorityLevel = "urgent"
            reason = "deadline is overdue, today, or tomorrow"
        elif days_until_due <= 5:
            priority = "important"
            reason = "deadline is within 2-5 days"
        else:
            priority = "low"
            reason = "deadline is not near"
        return DeadlinePriorityDecision(
            priority=priority,
            detected_deadline=detected_deadline,
            due_date=due_date,
            days_until_due=days_until_due,
            reason=reason,
        )

    if detected_intent == "action_request":
        return DeadlinePriorityDecision(
            priority="low",
            detected_deadline=None,
            due_date=None,
            days_until_due=None,
            reason="actionable email with no near deadline",
        )

    return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def cleanup_noise_artifacts(db: Session, email: Email, *, reason: str) -> tuple[int, int]:
    now = _utc_now()
    email.priority = "noise"
    email.task_extracted_at = email.task_extracted_at or now
    email.followup_evaluated_at = email.followup_evaluated_at or now
    deleted_tasks = db.query(Task).filter(Task.email_id == email.id).delete(synchronize_session=False)
    deleted_followups = (
        db.query(FollowUp)
        .filter(FollowUp.user_id == email.user_id, FollowUp.thread_id == email.thread_id)
        .delete(synchronize_session=False)
    )
    print(
        "NOISE CLEANUP ACTION:",
        {
            "email_id": email.id,
            "reason": reason,
            "deleted_tasks": deleted_tasks,
            "deleted_followups": deleted_followups,
        },
    )
    return deleted_tasks, deleted_followups


def apply_acknowledgement_classification(db: Session, email: Email) -> int:
    now = _utc_now()
    email.priority = "low"
    email.task_extracted_at = email.task_extracted_at or now
    email.followup_evaluated_at = email.followup_evaluated_at or now
    cleared_followups = (
        db.query(FollowUp)
        .filter(
            FollowUp.user_id == email.user_id,
            FollowUp.thread_id == email.thread_id,
            FollowUp.status == "open",
        )
        .update(
            {
                "needs_followup": False,
                "status": "resolved",
                "resolved_at": now,
            },
            synchronize_session=False,
        )
    )
    close_thread_if_work_resolved(
        db,
        user_id=email.user_id,
        thread_id=email.thread_id,
        reason="acknowledgement email received",
    )
    return cleared_followups


async def infer_priority(email_input: EmailPriorityInput) -> PriorityLevel:
    prompt = build_classification_prompt(email_input)
    print(
        "PRIORITY CLASSIFICATION REQUEST:",
        {
            "sender": email_input.sender,
            "subject": email_input.subject,
            "body_chars": len(email_input.body_cleaned),
            "prompt_chars": len(prompt),
        },
    )

    try:
        result = await generate_structured(
            prompt,
            PriorityClassificationResult,
            system=CLASSIFICATION_SYSTEM,
            schema_hint=CLASSIFICATION_SCHEMA_HINT,
            temperature=0.1,
            max_tokens=64,
        )
        priority = normalize_priority(result.priority)
        print("PRIORITY CLASSIFICATION AI RESULT:", {"priority": priority})
        return priority
    except (AIResponseParseError, ValueError):
        raw = await generate_text(
            prompt,
            system=CLASSIFICATION_SYSTEM + " JSON only.",
            temperature=0.0,
            max_tokens=64,
        )
        parsed = parse_structured_response(raw, PriorityClassificationResult)
        priority = normalize_priority(parsed.priority)
        print("PRIORITY CLASSIFICATION AI FALLBACK RESULT:", {"priority": priority})
        return priority


async def classify_email_record(
    db: Session,
    email: Email,
    *,
    commit: bool = True,
) -> ClassificationResult:
    started = perf_counter()
    print(
        "PRIORITY CLASSIFICATION EMAIL START:",
        {
            "email_id": email.id,
            "gmail_message_id": email.gmail_message_id,
            "existing_priority": email.priority,
            "has_cleaned_body": bool(email.body_cleaned),
            "processed_at": email.processed_at.isoformat() if email.processed_at else None,
        },
    )
    email_input = extract_classification_input(email)
    detected_intent = detect_email_intent(email)
    print(
        "PRIORITY CLASSIFICATION INTENT:",
        {
            "email_id": email.id,
            "detected_intent": detected_intent,
        },
    )
    if detected_intent == "acknowledgement":
        cleared_followups = apply_acknowledgement_classification(db, email)
        if commit:
            db.commit()
            db.refresh(email)
        print(
            "PRIORITY CLASSIFICATION DB UPDATE:",
            {
                "email_id": email.id,
                "detected_intent": detected_intent,
                "classification_reason": "acknowledgement/closure message",
                "assigned_priority": "low",
                "cleared_followups": cleared_followups,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return ClassificationResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            classified=True,
            priority="low",
            message="Acknowledgement email classified as low priority.",
        )

    noise = detect_noise_email(email)
    if noise.is_noise:
        deleted_tasks, deleted_followups = cleanup_noise_artifacts(db, email, reason=noise.reason or "noise")
        if commit:
            db.commit()
            db.refresh(email)
        print(
            "PRIORITY CLASSIFICATION PREFILTERED:",
            {
                "email_id": email.id,
                "detected_intent": detected_intent,
                "classification_reason": noise.reason,
                "assigned_priority": "noise",
                "priority": "noise",
                "reason": noise.reason,
                "deleted_existing_tasks": deleted_tasks,
                "deleted_existing_followups": deleted_followups,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return ClassificationResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            classified=True,
            priority="noise",
            message=f"Classified as noise: {noise.reason}.",
        )

    if email_input is None:
        if not email.processed_at:
            print(
                "PRIORITY CLASSIFICATION EMAIL SKIPPED:",
                {"email_id": email.id, "reason": "missing processed_at or cleaned body"},
            )
            return ClassificationResult(
                email_id=email.id,
                gmail_message_id=email.gmail_message_id,
                classified=False,
                priority=email.priority,
                message="Skipped: email must be processed before classification.",
            )
        email.priority = "noise"
        if commit:
            db.commit()
            db.refresh(email)
        print(
            "PRIORITY CLASSIFICATION DB UPDATE:",
            {
                "email_id": email.id,
                "detected_intent": detected_intent,
                "classification_reason": "empty cleaned body",
                "assigned_priority": "noise",
                "priority": "noise",
                "committed": commit,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return ClassificationResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            classified=True,
            priority="noise",
            message="Empty cleaned body; classified as noise.",
        )

    today = current_system_date()
    deterministic = deterministic_priority_decision(email, detected_intent=detected_intent, today=today)
    if deterministic is not None:
        email.priority = deterministic.priority
        if commit:
            db.commit()
            db.refresh(email)
        print(
            "PRIORITY CLASSIFICATION DEADLINE DECISION:",
            {
                "email_id": email.id,
                "detected_deadline": deterministic.detected_deadline,
                "current_date": today.isoformat(),
                "due_date": deterministic.due_date.isoformat() if deterministic.due_date else None,
                "days_until_due": deterministic.days_until_due,
                "classification_reason": deterministic.reason,
                "final_priority": deterministic.priority,
                "detected_intent": detected_intent,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return ClassificationResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            classified=True,
            priority=deterministic.priority,
            message=f"Priority classified by deadline rules: {deterministic.reason}.",
        )

    try:
        priority = await infer_priority(email_input)
        if priority == "noise":
            cleanup_noise_artifacts(db, email, reason="AI classified as noise")
        else:
            email.priority = priority
        if commit:
            db.commit()
            db.refresh(email)
        print(
            "PRIORITY CLASSIFICATION DB UPDATE:",
            {
                "email_id": email.id,
                "detected_intent": detected_intent,
                "classification_reason": "AI priority classification",
                "assigned_priority": priority,
                "priority": priority,
                "committed": commit,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return ClassificationResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            classified=True,
            priority=priority,
            message="Priority classified successfully.",
        )
    except Exception as exc:
        print(
            "PRIORITY CLASSIFICATION ERROR:",
            {
                "email_id": email.id,
                "error_type": exc.__class__.__name__,
                "message": str(exc),
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return ClassificationResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            classified=False,
            priority=email.priority,
            message=f"Classification failed: {exc}",
        )


def get_unclassified_emails(db: Session, user_id: int) -> list[Email]:
    return (
        db.query(Email)
        .filter(Email.user_id == user_id, Email.priority.is_(None))
        .order_by(Email.received_at.desc())
        .all()
    )


async def classify_unclassified_for_user(
    db: Session,
    user_id: int,
) -> BatchClassificationResult:
    emails = get_unclassified_emails(db, user_id)
    return await classify_email_batch(db, emails)


async def classify_email_batch(
    db: Session,
    emails: list[Email],
) -> BatchClassificationResult:
    started = perf_counter()
    print("PRIORITY CLASSIFICATION BATCH START:", {"email_ids": [email.id for email in emails]})
    classified = 0
    skipped = 0
    failed = 0
    results: list[ClassificationResult] = []

    for email in emails:
        result = await classify_email_record(db, email, commit=False)
        results.append(result)
        if result.classified:
            classified += 1
        elif "skipped" in result.message.lower():
            skipped += 1
        else:
            failed += 1

    if classified:
        db.commit()
        print(
            "PRIORITY CLASSIFICATION BATCH COMMIT:",
            {"classified": classified, "email_ids": [result.email_id for result in results if result.classified]},
        )
    print(
        "PRIORITY CLASSIFICATION BATCH RESULT:",
        {
            "classified": classified,
            "skipped": skipped,
            "failed": failed,
            "results": [
                {
                    "email_id": result.email_id,
                    "classified": result.classified,
                    "priority": result.priority,
                    "message": result.message,
                }
                for result in results
            ],
            "duration_ms": round((perf_counter() - started) * 1000, 2),
        },
    )

    return BatchClassificationResult(
        classified=classified,
        skipped=skipped,
        failed=failed,
        results=results,
    )
