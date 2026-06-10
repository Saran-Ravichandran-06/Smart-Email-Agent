from app.ai.reply_generation import clean_reply_draft, truncate_text

FOLLOWUP_DRAFT_SYSTEM = (
    "You write brief professional follow-up emails. Be polite and concise. "
    "Do not invent attachments or meetings. Output only the email body."
)

MAX_CONTEXT_CHARS = 600


def build_followup_draft_prompt(
    *,
    subject: str,
    recipient_or_sender: str,
    reason: str,
    last_body: str,
) -> str:
    body = truncate_text(last_body, MAX_CONTEXT_CHARS)
    reason_hint = {
        "stale_incoming_no_reply": "You received this and have not replied in over 48 hours.",
        "priority_thread_stale": "This urgent/important thread has been inactive.",
        "sent_awaiting_response": "You sent this and have not received a response.",
    }.get(reason, "This conversation needs a follow-up.")

    return (
        "Write a short follow-up email (under 80 words).\n"
        f"Context: {reason_hint}\n"
        f"Other party: {recipient_or_sender}\n"
        f"Subject: {subject}\n"
        f"Last message excerpt: {body}\n\n"
        "Follow-up email body:"
    )
