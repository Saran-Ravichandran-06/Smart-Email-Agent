import axios, { type AxiosError, type AxiosRequestConfig } from 'axios'

import type { ApiErrorPayload } from '@/api/types'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number | null
  payload: ApiErrorPayload | null

  constructor(
    message: string,
    status: number | null = null,
    payload: ApiErrorPayload | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60_000,
})

apiClient.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
)

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorPayload>) => {
    const status = error.response?.status ?? null
    const payload = error.response?.data ?? null
    const message = extractErrorMessage(payload, error.message, status)
    return Promise.reject(new ApiError(message, status, payload))
  },
)

function extractErrorMessage(
  payload: ApiErrorPayload | null,
  fallback: string,
  status: number | null,
): string {
  if (payload?.detail) {
    if (typeof payload.detail === 'string') {
      return payload.detail
    }
    if (Array.isArray(payload.detail) && payload.detail.length > 0) {
      return payload.detail.map((item) => item.msg).join(', ')
    }
  }
  if (status) {
    return `${fallback} (${status})`
  }
  return fallback
}

export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.get<T>(url, config)
  return response.data
}

export async function apiPost<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await apiClient.post<T>(url, data, config)
  return response.data
}

export async function apiPatch<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await apiClient.patch<T>(url, data, config)
  return response.data
}
