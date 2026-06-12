import { ArrowLeft } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'

import FollowupStatus from '@/components/email/FollowupStatus'
import PriorityBadge from '@/components/email/PriorityBadge'
import TaskList from '@/components/email/TaskList'
import { buttonVariants } from '@/components/ui/button'
import ErrorState from '@/components/ui/ErrorState'
import { DetailSkeleton } from '@/components/ui/LoadingState'
import { useEmailDetail } from '@/hooks/useInbox'
import { formatDateTime } from '@/lib/format'

type EmailDetailProps = {
  emailId: number
}

export default function EmailDetail({ emailId }: EmailDetailProps) {
  const [searchParams] = useSearchParams()
  const from = searchParams.get('from')
  const followupId = searchParams.get('followupId')
  
  const backLink = from === 'followups' ? '/follow-ups' : '/'
  const backText = from === 'followups' ? 'Follow-Ups' : 'Inbox'
  const replyLink = from === 'followups' && followupId
    ? `/email/${emailId}/reply?from=followups&followupId=${followupId}`
    : `/email/${emailId}/reply?from=email`

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
  } = useEmailDetail(emailId)

  if (detailLoading && !selectedEmail) {
    return <DetailSkeleton />
  }

  if (detailError || !selectedEmail) {
    return (
      <div className="mx-auto max-w-md py-12">
        <ErrorState
          title="Failed to load email"
          message={detailError ?? 'Email not found.'}
          onRetry={reloadDetail}
          retryText="Retry Loading"
        />
        <div className="mt-4 text-center">
          <Link
            to={backLink}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-input bg-background px-3 text-xs font-medium hover:bg-accent text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            Back to {backText.toLowerCase()}
          </Link>
        </div>
      </div>
    )
  }

  const isNoise = selectedEmail.priority === 'noise'

  return (
    <div className="relative w-full">
      <div className="mb-4 xl:absolute xl:left-0 xl:top-0 xl:mb-0">
        <Link
          to={backLink}
          className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          {backText}
        </Link>
      </div>
      <div className="mx-auto w-full max-w-3xl">

      <header className="pb-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">
                {selectedEmail.subject || '(No subject)'}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                From {selectedEmail.sender}
              </p>
              <p className="text-xs text-muted-foreground">
                {formatDateTime(selectedEmail.received_at)}
              </p>
            </div>
            <PriorityBadge priority={selectedEmail.priority} />
          </div>
        </header>

        <div className="mt-6 space-y-8">
          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Email content
            </h2>
            <div className="rounded-md border border-border bg-card p-4">
              <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
                {cleanedBody ?? selectedEmail.body}
              </pre>
            </div>
          </section>

          {!isNoise && (
            <>
              <section>
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Extracted tasks
                </h2>
                <TaskList
                  tasks={tasks}
                  loading={tasksLoading}
                  error={tasksError}
                  onRetry={reloadDetail}
                />
              </section>

              <section>
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Follow-up status
                </h2>
            <FollowupStatus
              followup={threadFollowup}
              email={selectedEmail}
              emailId={selectedEmail.id}
              loading={detailLoading}
            />
              </section>

              <div className="pt-0">
                <Link className={buttonVariants()} to={replyLink}>
                  Generate draft
                </Link>
              </div>
            </>
          )}

          {isNoise && (
            <p className="text-sm text-muted-foreground">
              Noise email: tasks, follow-ups, and reply recommendations are skipped.
            </p>
          )}
          </div>
        </div>
      </div>
  )
}
