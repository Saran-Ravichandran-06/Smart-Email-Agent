import re
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter

from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.ai.exceptions import AIResponseParseError
from app.ai.parser import extract_json_payload, parse_structured_response
from app.ai.services import generate_text
from app.ai.task_extraction import (
    EXTRACTION_SYSTEM,
    EmailTaskInput,
    ExtractedTaskItem,
    TaskExtractionResult,
    build_task_extraction_prompt,
)
from app.models.email import Email
from app.models.task import Task
from app.services.noise_detection import detect_noise_email
from app.services.thread_state import close_thread_if_work_resolved, decide_task_creation_for_email
from app.utils.deadline import parse_deadline_value

VALID_TASK_STATUSES = frozenset({"pending", "in_progress", "completed", "cancelled"})
TASK_TITLE_MAX_CHARS = 300
TASK_ACTION_HINTS = (
    "approve",
    "complete",
    "submit",
    "send",
    "share",
    "review",
    "provide",
    "confirm",
    "prepare",
    "update",
    "schedule",
    "create",
    "finish",
    "check",
    "respond",
    "reply",
    "follow up",
    "fix",
    "discuss",
    "replace",
    "remove",
    "add",
    "publish",
    "launch",
)
BAD_TASK_PATTERNS = (
    r"^\s*```",
    r"^\s*//",
    r"^\s*#",
    r"^\s*\{?\s*\"?(tasks?|deadline|due|items|actions|todos)\"?\s*:?",
    r"^\s*[\[\]\{\},]\s*$",
    r"\bassuming today\b",
    r"\bjson\b",
)


@dataclass(frozen=True)
class TaskExtractionItemResult:
    task_text: str
    created: bool
    message: str


@dataclass(frozen=True)
class EmailTaskExtractionResult:
    email_id: int
    gmail_message_id: str
    extracted: bool
    tasks_found: int
    tasks_created: int
    tasks_skipped: int
    message: str
    items: list[TaskExtractionItemResult]


@dataclass(frozen=True)
class BatchTaskExtractionResult:
    processed: int
    skipped: int
    failed: int
    tasks_created: int
    results: list[EmailTaskExtractionResult]


def extract_task_input(email: Email) -> EmailTaskInput | None:
    body = (email.body_cleaned or "").strip()
    if not body:
        return None
    return EmailTaskInput(
        subject=(email.subject or "(No Subject)").strip()[:512],
        body_cleaned=body,
    )


def normalize_task_text(text: str) -> str:
    return " ".join(text.strip().split()).lower()


def sanitize_task_title(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None

    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    text = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", text).strip()
    text = re.sub(r"^(?:task|action|todo|title)\s*[:=\-]\s*", "", text, flags=re.IGNORECASE).strip()
    text = text.strip().strip(",").strip()
    text = text.strip('"').strip("'").strip()

    if not text or text.lower() in {"null", "none", "n/a", "no tasks", "[]", "{}"}:
        return None
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in BAD_TASK_PATTERNS):
        return None
    if any(char in text for char in "{}[]"):
        return None
    if ":" in text and re.match(r'^\s*"?[a-z_ ]+"?\s*:', text, flags=re.IGNORECASE):
        return None
    if len(text) < 4 or len(text) > TASK_TITLE_MAX_CHARS:
        return None

    cleaned = " ".join(text.split())
    if not any(hint in cleaned.lower() for hint in TASK_ACTION_HINTS):
        # Keep short imperative fragments, reject explanations/metadata.
        if len(cleaned.split()) > 8:
            return None
    return cleaned


def sanitize_deadline(raw: object) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raw = str(raw)
    text = raw.strip().strip('"').strip("'")
    if not text or text.lower() in {"null", "none", "n/a"}:
        return None
    if any(char in text for char in "{}[]"):
        return None
    if len(text) > 80:
        return None
    return " ".join(text.split())


def infer_deadline_from_text(text: str) -> str | None:
    lowered = text.lower()
    deadline_patterns = (
        r"\bby\s+(tomorrow|today|friday|monday|tuesday|wednesday|thursday|saturday|sunday)\b",
        r"\bby\s+([a-z]+\s+\d{1,2}(?:,\s*\d{4})?)\b",
        r"\bdue\s+(tomorrow|today|friday|monday|tuesday|wednesday|thursday|saturday|sunday)\b",
    )
    for pattern in deadline_patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def strip_deadline_clause(text: str) -> str:
    text = re.sub(
        r"\s+\bby\s+(tomorrow|today|friday|monday|tuesday|wednesday|thursday|saturday|sunday)\b\.?\??$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def deterministic_task_fallback(email_input: EmailTaskInput) -> TaskExtractionResult:
    body = email_input.body_cleaned
    default_deadline = infer_deadline_from_text(body)
    tasks: list[ExtractedTaskItem] = []

    sentence_parts = re.split(r"(?<=[.!?])\s+|\n+", body)
    for part in sentence_parts:
        sentence = " ".join(part.strip().split())
        if not sentence:
            continue
        lowered = sentence.lower()
        task_text: str | None = None

        if lowered.startswith("please "):
            task_text = sentence[7:]
        elif lowered.startswith("also "):
            task_text = sentence[5:]
        elif lowered.startswith("can you ") and "finish this" not in lowered:
            task_text = sentence[8:]
        elif lowered.startswith("could you "):
            task_text = sentence[10:]

        if task_text:
            task_text = strip_deadline_clause(task_text)
            title = sanitize_task_title(task_text)
            if title:
                tasks.append(ExtractedTaskItem(task=title, deadline=default_deadline))

    print(
        "TASK EXTRACTION DETERMINISTIC FALLBACK:",
        {
            "subject": email_input.subject,
            "default_deadline": default_deadline,
            "tasks": [{"task": task.task, "deadline": task.deadline} for task in tasks],
        },
    )
    return TaskExtractionResult(tasks=tasks)


def task_already_exists(db: Session, email_id: int, task_text: str) -> bool:
    normalized = normalize_task_text(task_text)
    existing = db.query(Task.task_text).filter(Task.email_id == email_id).all()
    return any(normalize_task_text(row[0]) == normalized for row in existing)


def task_already_exists_in_thread(db: Session, email: Email, task_text: str) -> bool:
    normalized = normalize_task_text(task_text)
    existing = (
        db.query(Task.task_text)
        .join(Email, Task.email_id == Email.id)
        .filter(Email.user_id == email.user_id, Email.thread_id == email.thread_id)
        .all()
    )
    return any(normalize_task_text(row[0]) == normalized for row in existing)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def should_skip_task_extraction(email: Email) -> tuple[bool, str | None]:
    noise = detect_noise_email(email)
    return noise.is_noise, noise.reason


def _task_from_mapping(item: dict) -> ExtractedTaskItem | None:
    task = item.get("task") or item.get("action") or item.get("todo") or item.get("title")
    task_title = sanitize_task_title(task)
    if not task_title:
        return None
    deadline = item.get("deadline") or item.get("due") or item.get("due_date")
    return ExtractedTaskItem(task=task_title, deadline=sanitize_deadline(deadline))


def _tasks_from_payload(payload) -> list[ExtractedTaskItem]:
    if isinstance(payload, dict):
        raw_tasks = payload.get("tasks") or payload.get("items") or payload.get("actions") or payload.get("todos")
        if isinstance(raw_tasks, list):
            tasks: list[ExtractedTaskItem] = []
            for raw in raw_tasks:
                item = _task_from_mapping(raw) if isinstance(raw, dict) else None
                if item is None:
                    title = sanitize_task_title(raw)
                    item = ExtractedTaskItem(task=title, deadline=None) if title else None
                if item is not None and item.task.strip():
                    tasks.append(item)
            return tasks
        mapped = _task_from_mapping(payload)
        return [mapped] if mapped else []

    if isinstance(payload, list):
        tasks: list[ExtractedTaskItem] = []
        for raw in payload:
            if isinstance(raw, dict):
                mapped = _task_from_mapping(raw)
                if mapped:
                    tasks.append(mapped)
            else:
                title = sanitize_task_title(raw)
                if title:
                    tasks.append(ExtractedTaskItem(task=title, deadline=None))
        return tasks

    return []


def parse_task_extraction_lenient(raw: str) -> TaskExtractionResult:
    try:
        parsed = parse_structured_response(raw, TaskExtractionResult)
        sanitized = [
            ExtractedTaskItem(task=title, deadline=sanitize_deadline(item.deadline))
            for item in parsed.tasks
            if (title := sanitize_task_title(item.task))
        ]
        print(
            "TASK EXTRACTION PARSE STRUCTURED:",
            {
                "raw_task_count": len(parsed.tasks),
                "sanitized_task_count": len(sanitized),
                "tasks": [{"task": item.task, "deadline": item.deadline} for item in sanitized],
            },
        )
        return TaskExtractionResult(tasks=sanitized)
    except AIResponseParseError:
        pass

    try:
        payload = extract_json_payload(raw)
        tasks = _tasks_from_payload(payload)
        print(
            "TASK EXTRACTION PARSE JSON PAYLOAD:",
            {
                "payload_type": type(payload).__name__,
                "sanitized_task_count": len(tasks),
                "tasks": [{"task": item.task, "deadline": item.deadline} for item in tasks],
            },
        )
        if tasks:
            return TaskExtractionResult(tasks=tasks)
    except AIResponseParseError:
        pass

    tasks: list[ExtractedTaskItem] = []
    for line in raw.splitlines():
        cleaned = sanitize_task_title(line)
        if cleaned:
            tasks.append(ExtractedTaskItem(task=cleaned, deadline=None))

    print(
        "TASK EXTRACTION PARSE LINE FALLBACK:",
        {
            "sanitized_task_count": len(tasks),
            "tasks": [{"task": item.task, "deadline": item.deadline} for item in tasks],
        },
    )
    return TaskExtractionResult(tasks=tasks)


async def infer_tasks(email_input: EmailTaskInput) -> TaskExtractionResult:
    prompt = build_task_extraction_prompt(email_input)
    print(
        "TASK EXTRACTION REQUEST:",
        {
            "subject": email_input.subject,
            "body_chars": len(email_input.body_cleaned),
            "prompt_chars": len(prompt),
        },
    )

    raw = await generate_text(
        prompt,
        system=EXTRACTION_SYSTEM + " Keep the response short.",
        temperature=0.0,
        max_tokens=180,
    )
    print("TASK EXTRACTION RAW MODEL OUTPUT:", {"subject": email_input.subject, "raw": raw})
    result = parse_task_extraction_lenient(raw)
    if not result.tasks:
        result = deterministic_task_fallback(email_input)
    print(
        "TASK EXTRACTION AI RESULT:",
        {
            "raw_chars": len(raw or ""),
            "tasks": [{"task": item.task, "deadline": item.deadline} for item in result.tasks],
        },
    )
    return result


def save_extracted_tasks(
    db: Session,
    email: Email,
    extraction: TaskExtractionResult,
) -> tuple[int, int, list[TaskExtractionItemResult]]:
    created = 0
    skipped = 0
    items: list[TaskExtractionItemResult] = []

    for entry in extraction.tasks:
        print(
            "TASK EXTRACTION VALIDATION START:",
            {"email_id": email.id, "raw_task": entry.task, "raw_deadline": entry.deadline},
        )
        task_text = sanitize_task_title(entry.task)
        if not task_text:
            print(
                "TASK EXTRACTION VALIDATION REJECTED:",
                {"email_id": email.id, "raw_task": entry.task, "reason": "invalid sanitized title"},
            )
            skipped += 1
            items.append(
                TaskExtractionItemResult(
                    task_text="",
                    created=False,
                    message="Skipped empty task text.",
                )
            )
            continue

        if task_already_exists_in_thread(db, email, task_text):
            print(
                "TASK EXTRACTION DB INSERT SKIPPED:",
                {
                    "email_id": email.id,
                    "thread_id": email.thread_id,
                    "task": task_text,
                    "reason": "duplicate in thread",
                },
            )
            skipped += 1
            items.append(
                TaskExtractionItemResult(
                    task_text=task_text,
                    created=False,
                    message="Skipped duplicate task for this email.",
                )
            )
            continue

        deadline_dt, deadline_text = parse_deadline_value(
            sanitize_deadline(entry.deadline),
            reference=email.received_at,
        )
        print(
            "TASK EXTRACTION VALIDATION ACCEPTED:",
            {
                "email_id": email.id,
                "task": task_text,
                "deadline": entry.deadline,
                "deadline_text": deadline_text,
            },
        )

        task = Task(
            email_id=email.id,
            task_text=task_text[:4000],
            deadline=deadline_dt,
            deadline_text=deadline_text,
            status="pending",
        )
        db.add(task)
        print(
            "TASK EXTRACTION DB INSERT:",
            {
                "email_id": email.id,
                "task": task.task_text,
                "deadline_text": deadline_text,
                "status": task.status,
            },
        )
        created += 1
        items.append(
            TaskExtractionItemResult(
                task_text=task_text,
                created=True,
                message="Task saved.",
            )
        )

    return created, skipped, items


async def extract_tasks_for_email(
    db: Session,
    email: Email,
    *,
    commit: bool = True,
) -> EmailTaskExtractionResult:
    started = perf_counter()
    print(
        "TASK EXTRACTION EMAIL START:",
        {
            "email_id": email.id,
            "thread_id": email.thread_id,
            "gmail_message_id": email.gmail_message_id,
            "has_cleaned_body": bool(email.body_cleaned),
            "cleaned_body_chars": len(email.body_cleaned or ""),
        },
    )
    decision = decide_task_creation_for_email(db, email)
    print(
        "TASK CREATION DECISION:",
        {
            "email_id": email.id,
            "thread_id": email.thread_id,
            "thread_state": decision.thread_state,
            "existing_task_count": decision.existing_task_count,
            "task_creation_decision": decision.should_create,
            "reason_for_decision": decision.reason,
        },
    )
    if not decision.should_create:
        email.task_extracted_at = _utc_now()
        if commit:
            db.commit()
            db.refresh(email)
        return EmailTaskExtractionResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            extracted=True,
            tasks_found=0,
            tasks_created=0,
            tasks_skipped=0,
            message=f"Skipped task extraction: {decision.reason}.",
            items=[],
        )

    skip, skip_reason = should_skip_task_extraction(email)
    if skip:
        email.task_extracted_at = _utc_now()
        if commit:
            db.commit()
            db.refresh(email)
        print(
            "TASK EXTRACTION EMAIL PREFILTERED:",
            {
                "email_id": email.id,
                "reason": skip_reason,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return EmailTaskExtractionResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            extracted=True,
            tasks_found=0,
            tasks_created=0,
            tasks_skipped=0,
            message=f"Skipped task extraction: {skip_reason}.",
            items=[],
        )

    email_input = extract_task_input(email)

    if email_input is None:
        email.task_extracted_at = _utc_now()
        if commit:
            db.commit()
            db.refresh(email)
        print("TASK EXTRACTION EMAIL SKIPPED:", {"email_id": email.id, "reason": "missing body_cleaned"})
        return EmailTaskExtractionResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            extracted=True,
            tasks_found=0,
            tasks_created=0,
            tasks_skipped=0,
            message="Skipped: email must be processed (body_cleaned required).",
            items=[],
        )

    try:
        extraction = await infer_tasks(email_input)
        print(
            "TASK EXTRACTION PARSED TASKS:",
            {
                "email_id": email.id,
                "tasks": [{"task": item.task, "deadline": item.deadline} for item in extraction.tasks],
            },
        )
        created, skipped, items = save_extracted_tasks(db, email, extraction)
        email.task_extracted_at = _utc_now()

        if commit:
            db.commit()
            print(
                "TASK EXTRACTION EMAIL COMMIT:",
                {
                    "email_id": email.id,
                    "created": created,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                },
            )

        tasks_found = len(extraction.tasks)
        if tasks_found == 0:
            message = "No actionable tasks found."
        else:
            message = f"Extracted {tasks_found} task(s); created {created}, skipped {skipped}."

        return EmailTaskExtractionResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            extracted=True,
            tasks_found=tasks_found,
            tasks_created=created,
            tasks_skipped=skipped,
            message=message,
            items=items,
        )
    except Exception as exc:
        email.task_extracted_at = _utc_now()
        if commit:
            db.commit()
            db.refresh(email)
        print(
            "TASK EXTRACTION ERROR:",
            {
                "email_id": email.id,
                "error_type": exc.__class__.__name__,
                "message": str(exc),
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
        )
        return EmailTaskExtractionResult(
            email_id=email.id,
            gmail_message_id=email.gmail_message_id,
            extracted=True,
            tasks_found=0,
            tasks_created=0,
            tasks_skipped=0,
            message=f"Task extraction produced no usable tasks after parser recovery: {exc}",
            items=[],
        )


def get_emails_without_tasks(db: Session, user_id: int) -> list[Email]:
    has_tasks = exists().where(Task.email_id == Email.id)
    emails = (
        db.query(Email)
        .filter(
            Email.user_id == user_id,
            Email.body_cleaned.isnot(None),
            Email.task_extracted_at.is_(None),
            ~has_tasks,
        )
        .order_by(Email.received_at.desc())
        .all()
    )
    print(
        "TASK EXTRACTION DB QUERY [emails without tasks]:",
        {"user_id": user_id, "email_ids": [email.id for email in emails]},
    )
    return emails


async def extract_tasks_for_user(db: Session, user_id: int) -> BatchTaskExtractionResult:
    emails = get_emails_without_tasks(db, user_id)
    return await extract_tasks_batch(db, emails)


async def extract_tasks_batch(
    db: Session,
    emails: list[Email],
) -> BatchTaskExtractionResult:
    started = perf_counter()
    print("TASK EXTRACTION BATCH START:", {"email_ids": [email.id for email in emails]})
    processed = 0
    skipped = 0
    failed = 0
    tasks_created = 0
    results: list[EmailTaskExtractionResult] = []

    for email in emails:
        result = await extract_tasks_for_email(db, email, commit=False)
        results.append(result)
        if result.extracted:
            processed += 1
            tasks_created += result.tasks_created
        elif "skipped" in result.message.lower():
            skipped += 1
        else:
            failed += 1

    if processed:
        db.commit()
        print(
            "TASK EXTRACTION BATCH COMMIT:",
            {"processed": processed, "tasks_created": tasks_created},
        )
    print(
        "TASK EXTRACTION BATCH RESULT:",
        {
            "processed": processed,
            "skipped": skipped,
            "failed": failed,
            "tasks_created": tasks_created,
            "duration_ms": round((perf_counter() - started) * 1000, 2),
            "results": [
                {
                    "email_id": result.email_id,
                    "extracted": result.extracted,
                    "tasks_found": result.tasks_found,
                    "tasks_created": result.tasks_created,
                    "message": result.message,
                }
                for result in results
            ],
        },
    )

    return BatchTaskExtractionResult(
        processed=processed,
        skipped=skipped,
        failed=failed,
        tasks_created=tasks_created,
        results=results,
    )


def update_task_status(db: Session, task: Task, status: str) -> Task:
    normalized = status.strip().lower()
    if normalized not in VALID_TASK_STATUSES:
        raise ValueError(
            f"Invalid status. Use one of: {', '.join(sorted(VALID_TASK_STATUSES))}"
        )
    task.status = normalized
    if task.email:
        close_thread_if_work_resolved(
            db,
            user_id=task.email.user_id,
            thread_id=task.email.thread_id,
            reason="all tasks completed after task status update",
        )
    db.commit()
    db.refresh(task)
    return task
