from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.exceptions import (
    OllamaConnectionError,
    OllamaInferenceError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)
from app.auth.session import get_current_user
from app.database.session import get_db
from app.models.followup import FollowUp
from app.models.user import User
from app.schemas.followup import (
    FollowUpDraftResponse,
    FollowUpResolveResponse,
    FollowUpResponse,
    FollowUpTaskInfo,
    FollowUpScanResponse,
)
from app.services.followup_detection import (
    FOLLOWUP_STATUS_RESOLVED,
    get_followup_for_user,
    list_open_followups,
    mark_followup_resolved,
    scan_followups_for_user,
)
from app.services.followup_draft import generate_followup_draft
from app.services.task_extraction import sanitize_task_title

router = APIRouter(prefix="/followups", tags=["followups"])


def _followup_response(followup: FollowUp) -> FollowUpResponse:
    latest_email = followup.latest_email
    raw_tasks = latest_email.tasks if latest_email else []
    tasks = []
    for task in raw_tasks:
        cleaned = sanitize_task_title(task.task_text)
        if cleaned:
            task.task_text = cleaned
            tasks.append(task)
    pending_count = sum(1 for task in tasks if task.status != "completed")
    completed_count = sum(1 for task in tasks if task.status == "completed")
    task_count = len(tasks)

    if task_count == 0:
        task_summary = "No tasks extracted"
    elif pending_count == 0:
        task_summary = f"All {task_count} task(s) completed"
    elif completed_count == 0:
        task_summary = f"{pending_count} pending task(s)"
    else:
        task_summary = f"{pending_count} pending, {completed_count} completed"

    return FollowUpResponse(
        id=followup.id,
        user_id=followup.user_id,
        thread_id=followup.thread_id,
        last_activity=followup.last_activity,
        needs_followup=followup.needs_followup,
        reason=followup.reason,
        status=followup.status,
        draft_text=followup.draft_text,
        resolved_at=followup.resolved_at,
        latest_email_id=followup.latest_email_id,
        latest_email_sender=latest_email.sender if latest_email else None,
        latest_email_subject=latest_email.subject if latest_email else None,
        task_count=task_count,
        pending_task_count=pending_count,
        completed_task_count=completed_count,
        task_status_summary=task_summary,
        tasks=[
            FollowUpTaskInfo(
                id=task.id,
                task_text=task.task_text,
                status=task.status,
            )
            for task in tasks
        ],
        priority_snapshot=followup.priority_snapshot,
        created_at=followup.created_at,
    )


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
        detail="Follow-up operation failed.",
    )


@router.post("/scan", response_model=FollowUpScanResponse)
def scan_followups(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUpScanResponse:
    result = scan_followups_for_user(db, user)
    return FollowUpScanResponse(
        message="Follow-up scan completed.",
        scanned_threads=result.scanned_threads,
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        cleared=result.cleared,
        followup_ids=result.candidates,
    )


@router.get("", response_model=list[FollowUpResponse])
def list_followup_suggestions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FollowUpResponse]:
    followups = list_open_followups(db, user.id)
    print(
        "FOLLOWUP API DB QUERY [list open followups]:",
        {
            "user_id": user.id,
            "followup_ids": [followup.id for followup in followups],
            "latest_email_ids": [followup.latest_email_id for followup in followups],
            "thread_ids": [followup.thread_id for followup in followups],
        },
    )
    return [_followup_response(followup) for followup in followups]


@router.post("/{followup_id}/draft", response_model=FollowUpDraftResponse)
async def generate_followup_draft_endpoint(
    followup_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUpDraftResponse:
    followup = get_followup_for_user(db, user.id, followup_id)
    if followup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up not found.",
        )
    if followup.status == FOLLOWUP_STATUS_RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate draft for a resolved follow-up.",
        )

    try:
        draft = await generate_followup_draft(db, followup)
    except Exception as exc:
        raise _ai_http_exception(exc) from exc

    return FollowUpDraftResponse(
        followup_id=followup.id,
        thread_id=followup.thread_id,
        draft=draft,
        message="Follow-up draft generated successfully.",
    )


@router.patch("/{followup_id}/resolve", response_model=FollowUpResolveResponse)
def resolve_followup(
    followup_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUpResolveResponse:
    followup = get_followup_for_user(db, user.id, followup_id)
    if followup is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up not found.",
        )

    if followup.status == FOLLOWUP_STATUS_RESOLVED:
        return FollowUpResolveResponse(
            followup_id=followup.id,
            status=followup.status,
            message="Follow-up was already resolved.",
        )

    mark_followup_resolved(db, followup)
    return FollowUpResolveResponse(
        followup_id=followup.id,
        status=followup.status,
    )
