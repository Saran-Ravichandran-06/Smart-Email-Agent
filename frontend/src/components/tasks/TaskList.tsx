import { CheckSquare } from 'lucide-react'

import type { EmailResponse, TaskResponse } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import { ListSkeleton } from '@/components/ui/LoadingState'
import TaskCard from '@/components/tasks/TaskCard'
import { cleanTaskTitle } from '@/lib/tasks'

type TaskListProps = {
  tasks: TaskResponse[]
  emailMap: Record<number, EmailResponse>
  loading: boolean
  error: string | null
  updatingTaskId: number | null
  onMarkComplete: (taskId: number) => void
  onRetry?: () => void
}

export default function TaskList({
  tasks,
  emailMap,
  loading,
  error,
  updatingTaskId,
  onMarkComplete,
  onRetry,
}: TaskListProps) {
  if (loading && tasks.length === 0) {
    return (
      <div className="-mx-4">
        <ListSkeleton count={4} />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorState
        title="Failed to load tasks"
        message={error}
        onRetry={onRetry}
        retryText="Retry Loading Tasks"
      />
    )
  }

  if (tasks.length === 0) {
    return (
      <EmptyState
        title="No tasks found"
        description="Tasks from your emails will appear here. Try checking other status filters."
        icon={CheckSquare}
      />
    )
  }

  const cleanTasks = tasks.filter((task) => cleanTaskTitle(task.task_text))

  return (
    <ul className="space-y-3">
      {cleanTasks.map((task) => (
        <li key={task.id}>
          <TaskCard
            task={task}
            email={emailMap[task.email_id]}
            onMarkComplete={onMarkComplete}
            updating={updatingTaskId === task.id}
          />
        </li>
      ))}
    </ul>
  )
}

