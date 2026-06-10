from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.classification import PRIORITY_LABELS
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
from app.schemas.classification import (
    BatchPriorityClassificationResponse,
    PriorityClassificationResponse,
)
from app.services.priority_classification import (
    classify_email_record,
    classify_unclassified_for_user,
)

router = APIRouter(prefix="/emails", tags=["email-classification"])


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
        detail="Priority classification failed.",
    )


def _to_response(result) -> PriorityClassificationResponse:
    return PriorityClassificationResponse(
        email_id=result.email_id,
        gmail_message_id=result.gmail_message_id,
        classified=result.classified,
        priority=result.priority,
        message=result.message,
    )


@router.post("/classify", response_model=BatchPriorityClassificationResponse)
async def classify_all_unclassified(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BatchPriorityClassificationResponse:
    try:
        batch = await classify_unclassified_for_user(db, user.id)
    except Exception as exc:
        raise _ai_http_exception(exc) from exc

    if not batch.results:
        return BatchPriorityClassificationResponse(
            message="No unclassified emails found.",
            classified=0,
            skipped=0,
            failed=0,
            results=[],
        )

    return BatchPriorityClassificationResponse(
        message="Batch priority classification completed.",
        classified=batch.classified,
        skipped=batch.skipped,
        failed=batch.failed,
        results=[_to_response(item) for item in batch.results],
    )


@router.post("/{email_id}/classify", response_model=PriorityClassificationResponse)
async def classify_single_email(
    email_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PriorityClassificationResponse:
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
        result = await classify_email_record(db, email)
    except Exception as exc:
        raise _ai_http_exception(exc) from exc

    if not result.classified and "failed" in result.message.lower():
        raise _ai_http_exception(Exception(result.message))

    return _to_response(result)
