from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.exceptions import (
    AIResponseParseError,
    OllamaConnectionError,
    OllamaInferenceError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)
from app.auth.session import get_current_user
from app.database.session import get_db
from app.models.email import Email
from app.models.user import User
from app.schemas.task_extraction import (
    BatchTaskExtractionResponse,
    EmailTaskExtractionResponse,
    TaskExtractionItemResponse,
)
from app.services.task_extraction import (
    extract_tasks_for_email,
    extract_tasks_for_user,
)

router = APIRouter(prefix="/emails", tags=["task-extraction"])


def _ai_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, (OllamaConnectionError, OllamaModelNotFoundError)):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, OllamaTimeoutError):
        return HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc))
    if isinstance(exc, AIResponseParseError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, OllamaInferenceError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Task extraction failed.",
    )


def _to_response(result) -> EmailTaskExtractionResponse:
    return EmailTaskExtractionResponse(
        email_id=result.email_id,
        gmail_message_id=result.gmail_message_id,
        extracted=result.extracted,
        tasks_found=result.tasks_found,
        tasks_created=result.tasks_created,
        tasks_skipped=result.tasks_skipped,
        message=result.message,
        items=[
            TaskExtractionItemResponse(
                task_text=item.task_text,
                created=item.created,
                message=item.message,
            )
            for item in result.items
        ],
    )


@router.post("/extract-tasks", response_model=BatchTaskExtractionResponse)
async def extract_tasks_all(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BatchTaskExtractionResponse:
    try:
        batch = await extract_tasks_for_user(db, user.id)
    except Exception as exc:
        raise _ai_http_exception(exc) from exc

    if not batch.results:
        return BatchTaskExtractionResponse(
            message="No emails pending task extraction.",
            processed=0,
            skipped=0,
            failed=0,
            tasks_created=0,
            results=[],
        )

    return BatchTaskExtractionResponse(
        message="Batch task extraction completed.",
        processed=batch.processed,
        skipped=batch.skipped,
        failed=batch.failed,
        tasks_created=batch.tasks_created,
        results=[_to_response(item) for item in batch.results],
    )


@router.post("/{email_id}/extract-tasks", response_model=EmailTaskExtractionResponse)
async def extract_tasks_single(
    email_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailTaskExtractionResponse:
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

    try:
        result = await extract_tasks_for_email(db, email)
    except Exception as exc:
        raise _ai_http_exception(exc) from exc

    if not result.extracted and "failed" in result.message.lower():
        raise _ai_http_exception(Exception(result.message))

    return _to_response(result)
