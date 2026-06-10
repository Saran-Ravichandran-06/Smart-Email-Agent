export {
  apiClient,
  apiGet,
  apiPatch,
  apiPost,
  ApiError,
} from '@/api/client'
export { fetchAuthUser, getGoogleLoginUrl } from '@/api/auth'
export {
  fetchEmailById,
  fetchEmailCleaned,
  fetchEmails,
  syncEmails,
} from '@/api/emails'
export {
  fetchFollowups,
  generateFollowupDraft,
  resolveFollowup,
  scanFollowups,
} from '@/api/followups'
export { generateReplyDraft, regenerateReplyDraft } from '@/api/replies'
export { fetchTasks, updateTaskStatus } from '@/api/tasks'
export type {
  ApiErrorPayload,
  EmailResponse,
  AuthUserResponse,
  FollowUpDraftResponse,
  FollowUpResolveResponse,
  FollowUpScanResponse,
  FollowUpResponse,
  HealthResponse,
  ReplyDraftResponse,
  ReplyTone,
  TaskResponse,
} from '@/api/types'
