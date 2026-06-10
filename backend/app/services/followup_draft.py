from sqlalchemy.orm import Session

from app.ai.followup_draft import FOLLOWUP_DRAFT_SYSTEM, build_followup_draft_prompt
from app.ai.reply_generation import clean_reply_draft, is_reply_too_short
from app.ai.services import generate_text
from app.models.email import Email
from app.models.followup import FollowUp


async def generate_followup_draft(
    db: Session,
    followup: FollowUp,
) -> str:
    email: Email | None = None
    if followup.latest_email_id:
        email = db.query(Email).filter(Email.id == followup.latest_email_id).first()

    subject = email.subject if email else "(No Subject)"
    body = ""
    if email:
        body = (email.body_cleaned or email.body_raw or email.body or "").strip()
    counterparty = email.sender if email else "the recipient"

    prompt = build_followup_draft_prompt(
        subject=subject,
        recipient_or_sender=counterparty,
        reason=followup.reason or "stale_incoming_no_reply",
        last_body=body or "No message body available.",
    )

    raw = await generate_text(
        prompt,
        system=FOLLOWUP_DRAFT_SYSTEM,
        temperature=0.3,
        max_tokens=200,
    )
    draft = clean_reply_draft(raw)

    if is_reply_too_short(draft):
        raw = await generate_text(
            prompt,
            system=FOLLOWUP_DRAFT_SYSTEM + " Keep it brief but complete.",
            temperature=0.2,
            max_tokens=200,
        )
        draft = clean_reply_draft(raw)

    if is_reply_too_short(draft):
        raise ValueError("Failed to generate a valid follow-up draft.")

    followup.draft_text = draft
    db.commit()
    db.refresh(followup)
    return draft
