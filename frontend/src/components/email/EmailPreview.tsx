import { ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'

import FollowupStatus from '@/components/email/FollowupStatus'
import TaskList from '@/components/email/TaskList'
import EmptyState from '@/components/email/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import { DetailSkeleton } from '@/components/ui/LoadingState'
import { useEmailDetail } from '@/hooks/useInbox'
import { formatDateTime } from '@/lib/format'
import { useEmailStore } from '@/store/useEmailStore'

export default function EmailPreview() {
  const selectedEmailId = useEmailStore((s) => s.selectedEmailId)
  const {
    selectedEmail,
    cleanedBody,
    tasks,
    threadFollowup,
    detailLoading,
    tasksLoading,
    detailError,
    tasksError,
    reloadDetail,
  } = useEmailDetail(selectedEmailId)

  if (selectedEmailId === null) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <EmptyState
          title="Select an email"
          description="Choose a message from the list to preview its content and tasks."
        />
      </div>
    )
  }

  if (detailLoading && !selectedEmail) {
    return <DetailSkeleton />
  }

  if (detailError || !selectedEmail) {
    return (
      <div className="flex h-full items-center justify-center bg-background p-6">
        <div className="w-full max-w-sm">
          <ErrorState
            title="Failed to load email"
            message={detailError ?? 'Email details could not be retrieved.'}
            onRetry={reloadDetail}
            retryText="Retry Loading"
          />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 overflow-hidden bg-background">
      <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-[108px] shrink-0 items-center border-b border-border px-6 py-4">
        <div className="flex w-full flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold leading-tight">
              {selectedEmail.subject || '(No subject)'}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              From {selectedEmail.sender}
            </p>
            <p className="text-xs text-muted-foreground">
              {formatDateTime(selectedEmail.received_at)}
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            <Link
              to={`/email/${selectedEmail.id}`}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-input bg-background px-3 text-xs font-medium hover:bg-accent"
            >
              <ExternalLink className="size-3.5" />
              Full view
            </Link>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-6 py-4">
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Message
          </h3>
          <div className="h-65 overflow-y-auto rounded-md border border-border bg-card p-4">
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
              {cleanedBody ?? selectedEmail.body}
            </pre>
          </div>
        </section>

        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Extracted tasks
          </h3>
          <TaskList
            tasks={tasks}
            loading={tasksLoading}
            error={tasksError}
            compact
            onRetry={reloadDetail}
          />
        </section>

        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Follow-up status
          </h3>
          <FollowupStatus
            followup={threadFollowup}
            email={selectedEmail}
            emailId={selectedEmail.id}
            loading={detailLoading}
          />
        </section>
      </div>
      </div>
    </div>
  )
}
