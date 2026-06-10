from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.email import Email
from app.models.followup import FollowUp
from app.models.task import Task


def seed_mock_emails_and_relations(db: Session, user_id: int) -> tuple[int, int, int]:
    existing_count = db.query(Email).filter(Email.user_id == user_id).count()
    if existing_count > 0:
        return 0, existing_count, existing_count

    now = datetime.now(timezone.utc)

    e1 = Email(
        gmail_message_id="mock_msg_1",
        thread_id="mock_thread_budget",
        sender="jane.manager@company.com",
        recipient="mock.user@gmail.com",
        subject="URGENT: Approve Q2 marketing budget by Friday",
        body="Hi Team, we need to approve the Q2 marketing budget of $50k by this Friday. Please review the attached plan and send me your signoff as soon as possible. Also, John, please share the revised timeline.",
        body_raw="Hi Team, we need to approve the Q2 marketing budget of $50k by this Friday. Please review the attached plan and send me your signoff as soon as possible. Also, John, please share the revised timeline.",
        body_cleaned="Hi Team, we need to approve the Q2 marketing budget of $50k by this Friday. Please review the attached plan and send me your signoff as soon as possible. Also, John, please share the revised timeline.",
        processed_at=now,
        priority="urgent",
        received_at=now - timedelta(hours=2),
        user_id=user_id,
    )
    db.add(e1)
    db.flush()
    db.add(
        Task(
            email_id=e1.id,
            task_text="Approve the Q2 marketing budget of $50k",
            deadline_text="Friday",
            status="pending",
        )
    )

    e2 = Email(
        gmail_message_id="mock_msg_2",
        thread_id="mock_thread_mockups",
        sender="sarah.designer@company.com",
        recipient="mock.user@gmail.com",
        subject="Feedback needed on designer mockups",
        body="Hi, here are the latest product mockups for the landing page. Let me know what you think by Tuesday! I have attached the Figma link.",
        body_raw="Hi, here are the latest product mockups for the landing page. Let me know what you think by Tuesday! I have attached the Figma link.",
        body_cleaned="Hi, here are the latest product mockups for the landing page. Let me know what you think by Tuesday! I have attached the Figma link.",
        processed_at=now,
        priority="important",
        received_at=now - timedelta(days=3),
        user_id=user_id,
    )
    db.add(e2)
    db.flush()
    db.add(
        FollowUp(
            user_id=user_id,
            thread_id="mock_thread_mockups",
            last_activity=now - timedelta(days=3),
            needs_followup=True,
            reason="stale_incoming_no_reply",
            status="open",
            latest_email_id=e2.id,
            priority_snapshot="important",
        )
    )

    e3 = Email(
        gmail_message_id="mock_msg_3",
        thread_id="mock_thread_api",
        sender="mock.user@gmail.com",
        recipient="developer@partner.com",
        subject="Question about the API integration",
        body="Hey there, I wanted to check if you had a chance to look at the API endpoints we shared last week? We are waiting on your response to proceed.",
        body_raw="Hey there, I wanted to check if you had a chance to look at the API endpoints we shared last week? We are waiting on your response to proceed.",
        body_cleaned="Hey there, I wanted to check if you had a chance to look at the API endpoints we shared last week? We are waiting on your response to proceed.",
        processed_at=now,
        priority="low",
        received_at=now - timedelta(days=4),
        user_id=user_id,
    )
    db.add(e3)
    db.flush()
    db.add(
        FollowUp(
            user_id=user_id,
            thread_id="mock_thread_api",
            last_activity=now - timedelta(days=4),
            needs_followup=True,
            reason="sent_awaiting_response",
            status="open",
            latest_email_id=e3.id,
            priority_snapshot="low",
        )
    )

    e4 = Email(
        gmail_message_id="mock_msg_4",
        thread_id="mock_thread_review",
        sender="jane.manager@company.com",
        recipient="mock.user@gmail.com",
        subject="Budget review",
        body="Let's discuss the Q2 budget changes.",
        body_raw="Let's discuss the Q2 budget changes.",
        body_cleaned="Let's discuss the Q2 budget changes.",
        processed_at=now,
        priority="important",
        received_at=now - timedelta(days=2),
        user_id=user_id,
    )
    db.add(e4)

    e5 = Email(
        gmail_message_id="mock_msg_5",
        thread_id="mock_thread_review",
        sender="mock.user@gmail.com",
        recipient="jane.manager@company.com",
        subject="Re: Budget review",
        body="I think we should increase the marketing allocation by 10%.",
        body_raw="I think we should increase the marketing allocation by 10%.",
        body_cleaned="I think we should increase the marketing allocation by 10%.",
        processed_at=now,
        priority="important",
        received_at=now - timedelta(days=2) + timedelta(hours=4),
        user_id=user_id,
    )
    db.add(e5)

    e6 = Email(
        gmail_message_id="mock_msg_6",
        thread_id="mock_thread_review",
        sender="jane.manager@company.com",
        recipient="mock.user@gmail.com",
        subject="Re: Budget review",
        body="Agreed. Let's proceed with that. John, please update the spreadsheet by tomorrow.",
        body_raw="Agreed. Let's proceed with that. John, please update the spreadsheet by tomorrow.",
        body_cleaned="Agreed. Let's proceed with that. John, please update the spreadsheet by tomorrow.",
        processed_at=now,
        priority="important",
        received_at=now - timedelta(days=1, hours=12),
        user_id=user_id,
    )
    db.add(e6)
    db.flush()
    db.add(
        Task(
            email_id=e6.id,
            task_text="Update the budget spreadsheet with a 10% marketing allocation increase",
            deadline_text="Tomorrow",
            status="pending",
        )
    )

    db.commit()
    return 6, 0, 6
