import { apiGet, apiPatch, apiPost } from '@/api/client'
import type {
  FollowUpDraftResponse,
  FollowUpResolveResponse,
  FollowUpResponse,
  FollowUpScanResponse,
} from '@/api/types'

export async function fetchFollowups(): Promise<FollowUpResponse[]> {
  return apiGet<FollowUpResponse[]>('/api/followups')
}

export async function generateFollowupDraft(
  followupId: number,
): Promise<FollowUpDraftResponse> {
  return apiPost<FollowUpDraftResponse>(`/api/followups/${followupId}/draft`)
}

export async function resolveFollowup(
  followupId: number,
): Promise<FollowUpResolveResponse> {
  return apiPatch<FollowUpResolveResponse>(`/api/followups/${followupId}/resolve`)
}

export async function scanFollowups(): Promise<FollowUpScanResponse> {
  return apiPost<FollowUpScanResponse>('/api/followups/scan')
}
