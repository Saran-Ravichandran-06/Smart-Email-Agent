import { apiGet, apiPost } from '@/api/client'
import type {
  EmailCleanedResponse,
  EmailResponse,
  EmailSyncResponse,
} from '@/api/types'

export async function fetchEmails(priority?: string): Promise<EmailResponse[]> {
  const params = priority ? { priority } : undefined
  return apiGet<EmailResponse[]>('/api/emails', { params })
}

export async function fetchEmailById(emailId: number): Promise<EmailResponse> {
  return apiGet<EmailResponse>(`/api/emails/${emailId}`)
}

export async function fetchEmailCleaned(
  emailId: number,
): Promise<EmailCleanedResponse | null> {
  try {
    return await apiGet<EmailCleanedResponse>(`/api/emails/${emailId}/cleaned`)
  } catch {
    return null
  }
}

export async function syncEmails(): Promise<EmailSyncResponse> {
  return apiPost<EmailSyncResponse>('/api/emails/sync')
}
