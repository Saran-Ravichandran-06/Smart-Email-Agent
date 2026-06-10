import { create } from 'zustand'

import type { EmailResponse, TaskResponse } from '@/api/types'

export type TaskStatusFilter = 'all' | 'pending' | 'completed'

type TaskState = {
  tasks: TaskResponse[]
  taskEmailId: number | null
  emailMap: Record<number, EmailResponse>
  statusFilter: TaskStatusFilter
  pageLoaded: boolean
  tasksError: string | null
  updatingTaskId: number | null
  setTasks: (tasks: TaskResponse[], emailId?: number | null) => void
  setEmailMap: (map: Record<number, EmailResponse>) => void
  setStatusFilter: (filter: TaskStatusFilter) => void
  setPageLoaded: (loaded: boolean) => void
  setTasksError: (error: string | null) => void
  setUpdatingTaskId: (id: number | null) => void
  updateTaskInList: (task: TaskResponse) => void
  reset: () => void
}

const initialState = {
  tasks: [] as TaskResponse[],
  taskEmailId: null as number | null,
  emailMap: {} as Record<number, EmailResponse>,
  statusFilter: 'all' as TaskStatusFilter,
  pageLoaded: false,
  tasksError: null as string | null,
  updatingTaskId: null as number | null,
}

export const useTaskStore = create<TaskState>((set) => ({
  ...initialState,

  setTasks: (tasks, emailId = null) => set({ tasks, taskEmailId: emailId }),
  setEmailMap: (map) => set({ emailMap: map }),
  setStatusFilter: (filter) => set({ statusFilter: filter }),
  setPageLoaded: (loaded) => set({ pageLoaded: loaded }),
  setTasksError: (error) => set({ tasksError: error }),
  setUpdatingTaskId: (id) => set({ updatingTaskId: id }),
  updateTaskInList: (task) =>
    set((state) => ({
      tasks: state.tasks.map((item) => (item.id === task.id ? task : item)),
    })),
  reset: () => set(initialState),
}))
