import { apiGet, apiPatch } from '@/api/client'
import type { TaskResponse } from '@/api/types'

export type TaskStatusFilter = 'pending' | 'completed' | 'in_progress' | 'cancelled'

export async function fetchTasks(options?: {
  emailId?: number
  status?: TaskStatusFilter
}): Promise<TaskResponse[]> {
  const params: Record<string, string | number> = {}
  if (options?.emailId !== undefined) {
    params.email_id = options.emailId
  }
  if (options?.status !== undefined) {
    params.status = options.status
  }
  return apiGet<TaskResponse[]>('/api/tasks', {
    params: Object.keys(params).length > 0 ? params : undefined,
  })
}

export async function updateTaskStatus(
  taskId: number,
  status: string,
): Promise<TaskResponse> {
  return apiPatch<TaskResponse>(`/api/tasks/${taskId}`, { status })
}
