import { AlertCircle, CheckCircle2, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'

import type { FollowUpResponse } from '@/api/types'
import PriorityBadge from '@/components/email/PriorityBadge'
import { Button } from '@/components/ui/button'
import { formatDateTime } from '@/lib/format'
import { cleanTaskTitle } from '@/lib/tasks'

type FollowupCardProps = {
  followup: FollowUpResponse
  onGenerateDraft: (id: number) => void
  onResolve: (id: number) => void
  drafting?: boolean
  resolving?: boolean
}

export default function FollowupCard({
  followup,
  onGenerateDraft,
  onResolve,
  drafting = false,
  resolving = false,
}: FollowupCardProps) {
  const emailId = followup.latest_email_id
  const subject = followup.latest_email_subject || '(No subject)'
  const sender = followup.latest_email_sender || 'Unknown sender'
  const cleanTasks = followup.tasks.flatMap((task) => {
    const taskText = cleanTaskTitle(task.task_text)
    return taskText ? [{ ...task, task_text: taskText }] : []
  })
  const completedTasks = cleanTasks.filter((task) => task.status === 'completed').length
  const totalTasks = cleanTasks.length
  const pendingTasks = totalTasks - completedTasks
  const taskSummary =
    totalTasks === completedTasks
      ? 'Follow-up'
      : `${completedTasks}/${totalTasks} tasks completed`

  return (
    <article className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">
            {subject}
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            From {sender}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Last activity: {formatDateTime(followup.last_activity)}
          </p>
        </div>
        <PriorityBadge priority={followup.priority_snapshot} />
      </div>

      {totalTasks > 0 && (
        <div className="mt-3 rounded-md border border-border bg-muted/20 px-3 py-2">
          <ul className="space-y-2">
            {cleanTasks.map((task) => (
              <li key={task.id} className="flex items-start gap-2">
                {task.status === 'completed' ? (
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-500" />
                ) : (
                  <AlertCircle className="mt-0.5 size-4 shrink-0 text-destructive" />
                )}
                <div>
                  <p className="text-sm font-medium text-foreground">{task.task_text}</p>
                </div>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-foreground">{taskSummary}</span>
            <span
              className={
                pendingTasks > 0
                  ? 'rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-xs text-amber-900'
                  : 'rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-xs text-emerald-900'
              }
            >
              {pendingTasks > 0 ? 'Not ready for draft' : 'Ready to draft'}
            </span>
          </div>
        </div>
      )}

      {followup.draft_text && (
        <div className="mt-3 rounded-md border border-border bg-muted/20 p-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Follow-up suggestion
          </h4>
          <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
            {followup.draft_text}
          </pre>
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={!emailId || drafting || resolving}
          onClick={() => onGenerateDraft(followup.id)}
        >
          Generate draft
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={drafting || resolving}
          onClick={() => onResolve(followup.id)}
        >
          {resolving ? 'Resolving...' : 'Mark resolved'}
        </Button>
        {emailId && (
          <Link
            to={`/email/${emailId}?from=followups&followupId=${followup.id}`}
            className="inline-flex h-8 items-center gap-1 rounded-md border border-input bg-background px-3 text-xs font-medium hover:bg-accent"
          >
            <ExternalLink className="size-3" />
            Open email
          </Link>
        )}
      </div>
    </article>
  )
}
