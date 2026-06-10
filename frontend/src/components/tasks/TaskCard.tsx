import { ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'

import type { EmailResponse, TaskResponse } from '@/api/types'
import PriorityBadge from '@/components/email/PriorityBadge'
import { Button } from '@/components/ui/button'
import { formatDateTime } from '@/lib/format'
import { cleanTaskTitle } from '@/lib/tasks'
import { cn } from '@/lib/utils'

type TaskCardProps = {
  task: TaskResponse
  email?: EmailResponse
  onMarkComplete: (taskId: number) => void
  updating?: boolean
}

export default function TaskCard({
  task,
  email,
  onMarkComplete,
  updating = false,
}: TaskCardProps) {
  const isCompleted = task.status === 'completed'
  const taskTitle = cleanTaskTitle(task.task_text) ?? 'Task'
  const emailLabel = email
    ? `${email.sender} — ${email.subject || '(No subject)'}`
    : `Email #${task.email_id}`

  return (
    <article className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-4">
        <p
          className={cn(
            'text-sm leading-relaxed',
            isCompleted && 'text-muted-foreground',
          )}
        >
          {taskTitle}
        </p>
        {email?.priority && (
          <PriorityBadge priority={email.priority} className="mt-0.5 shrink-0" />
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span
          className={cn(
            'rounded border px-1.5 py-0.5 capitalize font-medium',
            isCompleted
              ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
              : 'border-amber-200 bg-amber-50 text-amber-900'
          )}
        >
          {task.status.replace('_', ' ')}
        </span>
        {task.deadline_text && <span>Due: {task.deadline_text}</span>}
        {task.deadline && !task.deadline_text && (
          <span>Due: {formatDateTime(task.deadline)}</span>
        )}
      </div>

      <p className="mt-2 truncate text-xs text-muted-foreground">{emailLabel}</p>

      <div className="mt-3 flex flex-wrap gap-2">
        {!isCompleted && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={updating}
            onClick={() => onMarkComplete(task.id)}
          >
            {updating ? 'Updating…' : 'Mark complete'}
          </Button>
        )}
        <Link
          to={`/email/${task.email_id}`}
          className="inline-flex h-8 items-center gap-1 rounded-md border border-input bg-background px-3 text-xs font-medium hover:bg-accent"
        >
          <ExternalLink className="size-3" />
          Open email
        </Link>
      </div>
    </article>
  )
}
