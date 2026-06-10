export type ApiErrorPayload = {
  detail?: string | { msg: string }[]
}

export type HealthResponse = {
  status: string
}

export type EmailResponse = {
  id: number
  gmail_message_id: string
  thread_id: string
  sender: string
  subject: string
  body: string
  priority: string | null
  summary: string | null
  task_extracted_at: string | null
  followup_evaluated_at: string | null
  gmail_synced_at: string | null
  gmail_deleted_at: string | null
  reply_sent_message_id: string | null
  reply_sent_thread_id: string | null
  reply_sent_at: string | null
  received_at: string
  user_id: number
  created_at: string
}

export type EmailCleanedResponse = {
  id: number
  metadata: {
    gmail_message_id: string
    thread_id: string
    sender: string
    recipient: string | null
    subject: string
    timestamp: string
  }
  body_raw: string
  body_cleaned: string
  processed_at: string | null
}

export type EmailSyncResponse = {
  message: string
  synced: number
  skipped: number
  total_fetched: number
}

export type TaskResponse = {
  id: number
  email_id: number
  task_text: string
  deadline: string | null
  deadline_text: string | null
  status: string
  created_at: string
}

export type FollowUpResponse = {
  id: number
  user_id: number
  thread_id: string
  last_activity: string
  needs_followup: boolean
  reason: string | null
  status: string
  draft_text: string | null
  resolved_at: string | null
  latest_email_id: number | null
  latest_email_sender: string | null
  latest_email_subject: string | null
  task_count: number
  pending_task_count: number
  completed_task_count: number
  task_status_summary: string | null
  tasks: {
    id: number
    task_text: string
    status: string
  }[]
  priority_snapshot: string | null
  created_at: string
}

export type ReplyDraftRequest = {
  tone: string
  previous_draft?: string | null
}

export type ReplyDraftResponse = {
  email_id: number
  thread_id: string
  tone: string
  draft: string
  context_messages_used: number
  regenerated: boolean
  message: string
}

export type ReplySendResponse = {
  email_id: number
  gmail_message_id: string
  thread_id: string
  sent_at: string
  message: string
}

export type ReplyTone = 'formal' | 'neutral' | 'friendly'

export type AuthUserResponse = {
  id: number
  email: string
  name: string | null
  google_id: string | null
  gmail_connected: boolean
}

export type FollowUpDraftResponse = {
  followup_id: number
  thread_id: string
  draft: string
  message: string
}

export type FollowUpResolveResponse = {
  followup_id: number
  status: string
  message: string
}

export type FollowUpScanResponse = {
  message: string
  scanned_threads: number
  created: number
  updated: number
  skipped: number
  cleared: number
  followup_ids: number[]
}
