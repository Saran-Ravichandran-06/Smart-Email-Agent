from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.session import get_current_user
from app.database.session import get_db
from app.models.email import Email
from app.models.user import User
from app.schemas.processing import (
    EmailBatchProcessResponse,
    EmailCleanedResponse,
    EmailMetadataResponse,
    EmailProcessItemResult,
)
from app.services.email_processing import (
    get_unprocessed_emails,
    process_single_email,
    process_unprocessed_for_user,
)

router = APIRouter(prefix="/emails", tags=["email-processing"])


def _to_cleaned_response(email: Email) -> EmailCleanedResponse:
    if not email.body_cleaned:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email has not been processed yet.",
        )

    return EmailCleanedResponse(
        id=email.id,
        metadata=EmailMetadataResponse(
            gmail_message_id=email.gmail_message_id,
            thread_id=email.thread_id,
            sender=email.sender,
            recipient=email.recipient,
            cc=email.cc,
            subject=email.subject,
            timestamp=email.received_at,
        ),
        body_raw=email.body_raw or email.body,
        body_cleaned=email.body_cleaned,
        processed_at=email.processed_at,
    )


@router.post("/process", response_model=EmailBatchProcessResponse)
def process_all_unprocessed_emails(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailBatchProcessResponse:
    unprocessed = get_unprocessed_emails(db, user.id)
    if not unprocessed:
        return EmailBatchProcessResponse(
            message="No unprocessed emails found.",
            processed=0,
            skipped=0,
            failed=0,
            results=[],
        )

    result = process_unprocessed_for_user(db, user.id)

    return EmailBatchProcessResponse(
        message="Batch email processing completed.",
        processed=result.processed,
        skipped=result.skipped,
        failed=result.failed,
        results=[
            EmailProcessItemResult(
                email_id=item.email_id,
                gmail_message_id=item.gmail_message_id,
                processed=item.processed,
                message=item.message,
            )
            for item in result.results
        ],
    )


@router.post("/{email_id}/process", response_model=EmailProcessItemResult)
def process_one_email(
    email_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailProcessItemResult:
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

    result = process_single_email(db, email)

    return EmailProcessItemResult(
        email_id=result.email_id,
        gmail_message_id=result.gmail_message_id,
        processed=result.processed,
        message=result.message,
    )


@router.get("/{email_id}/cleaned", response_model=EmailCleanedResponse)
def get_cleaned_email(
    email_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailCleanedResponse:
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

    return _to_cleaned_response(email)
