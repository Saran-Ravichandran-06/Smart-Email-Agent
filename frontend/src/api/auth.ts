import { apiGet } from '@/api/client'
import type { AuthUserResponse } from '@/api/types'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchAuthUser(): Promise<AuthUserResponse> {
  return apiGet<AuthUserResponse>('/api/auth/me')
}

export function getGoogleLoginUrl(): string {
  return `${API_BASE_URL}/api/auth/google/login?redirect=frontend`
}
