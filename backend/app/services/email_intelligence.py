from dataclasses import dataclass
from time import perf_counter

from datetime import datetime, timezone

from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.models.email import Email
from app.models.followup import FollowUp
from app.models.task import Task
from app.models.user import User
from app.services.followup_detection import FollowUpScanResult, scan_followups_for_user
from app.services.priority_classification import BatchClassificationResult, classify_email_batch
from app.services.noise_detection import detect_noise_email
from app.services.task_extraction import BatchTaskExtractionResult, extract_tasks_batch
from app.services.thread_state import (
    close_thread_if_work_resolved,
    detect_email_intent,
    reconcile_resolved_threads_for_user,
)


def _is_noise(email: Email) -> bool:
    return (email.priority or "").lower() == "noise"


def _cleanup_noise_artifacts(db: Session, user_id: int) -> None:
    now = datetime.now(timezone.utc)
    emails = (
        db.query(Email)
        .filter(Email.user_id == user_id)
        .all()
    )
    detected_noise_email_ids: list[int] = []
    for email in emails:
        noise = detect_noise_email(email)
        if noise.is_noise:
            if email.priority != "noise":
                detected_noise_email_ids.append(email.id)
                print(
                    "EMAIL INTELLIGENCE NOISE RECLASSIFY:",
                    {
                        "email_id": email.id,
                        "old_priority": email.priority,
                        "new_priority": "noise",
                        "reason": noise.reason,
                    },
                )
            email.priority = "noise"

    noise_emails = [email for email in emails if _is_noise(email)]
    if not noise_emails:
        return

    noise_email_ids = [email.id for email in noise_emails]
    noise_thread_ids = {email.thread_id for email in noise_emails}
    deleted_tasks = (
        db.query(Task)
        .filter(Task.email_id.in_(noise_email_ids))
        .delete(synchronize_session=False)
    )
    deleted_followups = (
        db.query(FollowUp)
        .filter(
            FollowUp.user_id == user_id,
            FollowUp.thread_id.in_(noise_thread_ids),
        )
        .delete(synchronize_session=False)
    )
    for email in noise_emails:
        email.task_extracted_at = email.task_extracted_at or now
        email.followup_evaluated_at = email.followup_evaluated_at or now
    db.commit()
    print(
        "EMAIL INTELLIGENCE NOISE CLEANUP:",
        {
            "user_id": user_id,
            "noise_email_ids": noise_email_ids,
            "newly_detected_noise_email_ids": detected_noise_email_ids,
            "deleted_tasks": deleted_tasks,
            "deleted_followups": deleted_followups,
        },
    )


def _cleanup_acknowledgement_artifacts(db: Session, user_id: int) -> None:
    now = datetime.now(timezone.utc)
    emails = db.query(Email).filter(Email.user_id == user_id).all()
    ack_email_ids: list[int] = []
    cleared_followups = 0
    for email in emails:
        if detect_email_intent(email) != "acknowledgement":
            continue
        ack_email_ids.append(email.id)
        email.priority = "low"
        email.task_extracted_at = email.task_extracted_at or now
        email.followup_evaluated_at = email.followup_evaluated_at or now
        cleared_followups += (
            db.query(FollowUp)
            .filter(
                FollowUp.user_id == user_id,
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
            user_id=user_id,
            thread_id=email.thread_id,
            reason="acknowledgement cleanup",
        )
    if ack_email_ids:
        db.commit()
    print(
        "EMAIL INTELLIGENCE ACK CLEANUP:",
        {
            "user_id": user_id,
            "ack_email_ids": ack_email_ids,
            "cleared_followups": cleared_followups,
        },
    )


@dataclass(frozen=True)
class PostSyncIntelligenceResult:
    email_ids: list[int]
    priority: BatchClassificationResult | None
    tasks: BatchTaskExtractionResult | None
    followups: FollowUpScanResult


def _load_post_sync_target_emails(db: Session, user_id: int, email_ids: list[int]) -> list[Email]:
    synced_ids = set(email_ids)
    has_tasks = exists().where(Task.email_id == Email.id)
    explicitly_unprocessed_ids = {
        row.id
        for row in (
            db.query(Email)
            .filter(
                Email.user_id == user_id,
                Email.body_cleaned.isnot(None),
                (
                    Email.priority.is_(None)
                    | (Email.task_extracted_at.is_(None) & ~has_tasks)
                    | Email.followup_evaluated_at.is_(None)
                ),
            )
            .all()
        )
    }
    target_ids = sorted(synced_ids | explicitly_unprocessed_ids)
    print(
        "EMAIL INTELLIGENCE DB QUERY [target emails]:",
        {
            "user_id": user_id,
            "synced_ids": sorted(synced_ids),
            "explicitly_unprocessed_ids": sorted(explicitly_unprocessed_ids),
            "target_ids": target_ids,
        },
    )

    if not target_ids:
        return []

    return (
        db.query(Email)
        .filter(Email.user_id == user_id, Email.id.in_(target_ids))
        .order_by(Email.received_at.desc())
        .all()
    )


async def run_post_sync_intelligence(
    db: Session,
    user: User,
    *,
    synced_email_ids: list[int],
) -> PostSyncIntelligenceResult:
    total_start = perf_counter()
    _cleanup_noise_artifacts(db, user.id)
    _cleanup_acknowledgement_artifacts(db, user.id)
    reconcile_resolved_threads_for_user(db, user.id)
    emails = _load_post_sync_target_emails(db, user.id, synced_email_ids)
    print(
        "EMAIL INTELLIGENCE START:",
        {
            "user_id": user.id,
            "email_ids": [email.id for email in emails],
        },
    )

    priority_result: BatchClassificationResult | None = None
    task_result: BatchTaskExtractionResult | None = None

    if emails:
        classification_targets = [email for email in emails if email.priority is None]
        classification_start = perf_counter()
        priority_result = await classify_email_batch(db, classification_targets)
        print(
            "EMAIL INTELLIGENCE TIMING [classification]:",
            {
                "duration_ms": round((perf_counter() - classification_start) * 1000, 2),
                "email_ids": [email.id for email in classification_targets],
            },
        )
        task_emails = [
            email
            for email in emails
            if email.task_extracted_at is None
            and not db.query(Task.id).filter(Task.email_id == email.id).first()
            and not _is_noise(email)
        ]
        print(
            "EMAIL INTELLIGENCE DB QUERY [task extraction targets]:",
            {
                "email_ids": [email.id for email in task_emails],
                "skipped_noise_email_ids": [email.id for email in emails if _is_noise(email)],
                "skipped_existing_task_email_ids": [
                    email.id for email in emails if email not in task_emails
                ],
            },
        )
        task_start = perf_counter()
        task_result = await extract_tasks_batch(db, task_emails)
        print(
            "EMAIL INTELLIGENCE TIMING [task extraction]:",
            {
                "duration_ms": round((perf_counter() - task_start) * 1000, 2),
                "email_ids": [email.id for email in task_emails],
            },
        )

    followup_target_thread_ids = {
        email.thread_id
        for email in emails
        if email.followup_evaluated_at is None and not _is_noise(email)
    }
    followup_start = perf_counter()
    if followup_target_thread_ids:
        followup_result = scan_followups_for_user(
            db,
            user,
            thread_ids=followup_target_thread_ids,
        )
    else:
        followup_result = FollowUpScanResult(
            scanned_threads=0,
            created=0,
            updated=0,
            skipped=0,
            cleared=0,
            candidates=[],
        )
    print(
        "EMAIL INTELLIGENCE TIMING [follow-up evaluation]:",
        {
            "duration_ms": round((perf_counter() - followup_start) * 1000, 2),
            "thread_ids": sorted(followup_target_thread_ids),
            "skipped_noise_thread_ids": sorted({email.thread_id for email in emails if _is_noise(email)}),
        },
    )
    print(
        "EMAIL INTELLIGENCE COMPLETE:",
        {
            "classified": priority_result.classified if priority_result else 0,
            "classification_failed": priority_result.failed if priority_result else 0,
            "tasks_created": task_result.tasks_created if task_result else 0,
            "task_extraction_failed": task_result.failed if task_result else 0,
            "followups_created": followup_result.created,
            "followups_updated": followup_result.updated,
            "followups_cleared": followup_result.cleared,
            "total_duration_ms": round((perf_counter() - total_start) * 1000, 2),
        },
    )

    return PostSyncIntelligenceResult(
        email_ids=[email.id for email in emails],
        priority=priority_result,
        tasks=task_result,
        followups=followup_result,
    )
