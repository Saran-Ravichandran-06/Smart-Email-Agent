from app.services.email_processing import BatchProcessResult, process_single_email, process_unprocessed_for_user
from app.services.email_sync import EmailSyncResult, sync_user_inbox
from app.services.priority_classification import (
    BatchClassificationResult,
    classify_email_record,
    classify_unclassified_for_user,
)
from app.services.followup_detection import FollowUpScanResult, scan_followups_for_user
from app.services.reply_generation import ReplyDraftResult, generate_reply_draft
from app.services.task_extraction import (
    BatchTaskExtractionResult,
    extract_tasks_for_email,
    extract_tasks_for_user,
    update_task_status,
)

__all__ = [
    "BatchClassificationResult",
    "BatchProcessResult",
    "BatchTaskExtractionResult",
    "EmailSyncResult",
    "classify_email_record",
    "classify_unclassified_for_user",
    "extract_tasks_for_email",
    "extract_tasks_for_user",
    "FollowUpScanResult",
    "generate_reply_draft",
    "scan_followups_for_user",
    "process_single_email",
    "ReplyDraftResult",
    "process_unprocessed_for_user",
    "sync_user_inbox",
    "update_task_status",
]
