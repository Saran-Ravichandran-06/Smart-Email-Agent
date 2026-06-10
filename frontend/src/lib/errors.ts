import { ApiError } from '@/api/client'

export function errorMessage(error: unknown, fallback = 'An unexpected error occurred.'): string {
  if (error instanceof ApiError) {
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return fallback
}
