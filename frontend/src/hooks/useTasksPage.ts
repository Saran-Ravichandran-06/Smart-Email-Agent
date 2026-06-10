import { useCallback, useEffect, useMemo } from 'react'

import { fetchEmails } from '@/api/emails'
import { fetchTasks, updateTaskStatus } from '@/api/tasks'
import { errorMessage } from '@/lib/errors'
import { useAppStore } from '@/store/useAppStore'
import { useTaskStore } from '@/store/useTaskStore'

let tasksPageInflight: Promise<void> | null = null

export function useTasksPage() {
  const tasks = useTaskStore((s) => s.tasks)
  const emailMap = useTaskStore((s) => s.emailMap)
  const statusFilter = useTaskStore((s) => s.statusFilter)
  const tasksError = useTaskStore((s) => s.tasksError)
  const updatingTaskId = useTaskStore((s) => s.updatingTaskId)
  const setTasks = useTaskStore((s) => s.setTasks)
  const setEmailMap = useTaskStore((s) => s.setEmailMap)
  const setStatusFilter = useTaskStore((s) => s.setStatusFilter)
  const setTasksError = useTaskStore((s) => s.setTasksError)
  const setUpdatingTaskId = useTaskStore((s) => s.setUpdatingTaskId)
  const updateTaskInList = useTaskStore((s) => s.updateTaskInList)

  const setLoading = useAppStore((s) => s.setLoading)
  const loading = useAppStore((s) => s.loading.tasks)

  const loadTasks = useCallback(async (force = false) => {
    void force
    if (tasksPageInflight) {
      return tasksPageInflight
    }
    tasksPageInflight = (async () => {
    setLoading('tasks', true)
    setTasksError(null)
    try {
      const [taskList, emails] = await Promise.all([
        fetchTasks(),
        fetchEmails(),
      ])
      setTasks(taskList, null)
      const map: Record<number, (typeof emails)[number]> = {}
      for (const email of emails) {
        map[email.id] = email
      }
      setEmailMap(map)
    } catch (error) {
      setTasksError(errorMessage(error, 'Failed to load tasks.'))
      setTasks([], null)
      setEmailMap({})
    } finally {
      setLoading('tasks', false)
      tasksPageInflight = null
    }
    })()
    return tasksPageInflight
  }, [setEmailMap, setLoading, setTasks, setTasksError])

  useEffect(() => {
    void loadTasks()
  }, [loadTasks])

  const filteredTasks = useMemo(() => {
    if (statusFilter === 'all') {
      return tasks
    }
    if (statusFilter === 'pending') {
      return tasks.filter(
        (task) => task.status === 'pending' || task.status === 'in_progress',
      )
    }
    return tasks.filter((task) => task.status === 'completed')
  }, [tasks, statusFilter])

  const markComplete = useCallback(
    async (taskId: number) => {
      setUpdatingTaskId(taskId)
      setTasksError(null)
      try {
        const updated = await updateTaskStatus(taskId, 'completed')
        updateTaskInList(updated)
      } catch (error) {
        setTasksError(errorMessage(error, 'Failed to update task.'))
      } finally {
        setUpdatingTaskId(null)
      }
    },
    [setTasksError, setUpdatingTaskId, updateTaskInList],
  )

  return {
    tasks: filteredTasks,
    emailMap,
    statusFilter,
    setStatusFilter,
    loading,
    tasksError,
    updatingTaskId,
    markComplete,
    reload: () => loadTasks(true),
  }
}
