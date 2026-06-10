import { apiPost } from '@/api/client'
import type {
  ReplyDraftRequest,
  ReplyDraftResponse,
  ReplySendResponse,
} from '@/api/types'

export async function generateReplyDraft(
  emailId: number,
  payload: ReplyDraftRequest,
): Promise<ReplyDraftResponse> {
  return apiPost<ReplyDraftResponse>(`/api/emails/${emailId}/reply`, payload)
}

export async function regenerateReplyDraft(
  emailId: number,
  payload: ReplyDraftRequest,
): Promise<ReplyDraftResponse> {
  return apiPost<ReplyDraftResponse>(
    `/api/emails/${emailId}/reply/regenerate`,
    payload,
  )
}

export async function sendReply(
  emailId: number,
  body: string,
): Promise<ReplySendResponse> {
  return apiPost<ReplySendResponse>(`/api/emails/${emailId}/reply/send`, {
    body,
  })
}
