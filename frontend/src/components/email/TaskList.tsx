import type { TaskResponse } from '@/api/types'
import ErrorState from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/LoadingState'
import { formatDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'

type TaskListProps = {
  tasks: TaskResponse[]
  loading?: boolean
  error?: string | null
  compact?: boolean
  onRetry?: () => void
}

function taskStatusClass(status: string) {
  return status === 'completed'
    ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
    : 'border-red-200 bg-red-50 text-red-900'
}

export default function TaskList({
  tasks,
  loading,
  error,
  compact = false,
  onRetry,
}: TaskListProps) {
  if (loading) {
    return (
      <div className="space-y-2 py-1">
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-14 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-1">
        <ErrorState
          title="Failed to load tasks"
          message={error}
          onRetry={onRetry}
          retryText="Retry"
        />
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <p className="inline-flex rounded-md border border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
        No tasks extracted from this email yet.
      </p>
    )
  }

  return (
    <ul className={compact ? 'space-y-2' : 'space-y-3'}>
      {tasks.map((task) => (
        <li
          key={task.id}
          className="rounded-md border border-border bg-background px-3 py-2"
        >
          <p className="text-sm font-medium text-foreground">{task.task_text}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span
              className={cn(
                'rounded border px-1.5 py-0.5 capitalize',
                taskStatusClass(task.status),
              )}
            >
              {task.status.replace('_', ' ')}
            </span>
            {task.deadline_text && <span>Due: {task.deadline_text}</span>}
            {task.deadline && !task.deadline_text && (
              <span>Due: {formatDateTime(task.deadline)}</span>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

