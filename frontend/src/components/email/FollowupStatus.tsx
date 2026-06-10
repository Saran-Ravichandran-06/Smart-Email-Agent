import type { EmailResponse, FollowUpResponse } from '@/api/types'
import { Skeleton } from '@/components/ui/LoadingState'
import { formatDateTime } from '@/lib/format'

type FollowupStatusProps = {
  followup: FollowUpResponse | undefined
  email?: EmailResponse
  emailId?: number
  loading?: boolean
}

export default function FollowupStatus({ followup, email, emailId, loading }: FollowupStatusProps) {
  void emailId

  if (loading) {
    return (
      <div className="space-y-2 py-1">
        <Skeleton className="h-6 w-36" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    )
  }

  if (!followup) {
    if (email?.reply_sent_at) {
      return (
        <div className="rounded-md border border-border bg-muted/30 px-3 py-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium capitalize">closed</span>
            <span className="rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-xs text-emerald-900">
              Follow-up provided
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Sent {formatDateTime(email.reply_sent_at)}
          </p>
        </div>
      )
    }

    return (
      <div className="inline-flex rounded-md border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
        No active follow-up for this thread.
      </div>
    )
  }

  return (
    <div className="rounded-md border border-border bg-muted/30 px-3 py-2 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium capitalize">{followup.status}</span>
        {followup.needs_followup && (
          <span className="rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-xs text-amber-900">
            Needs follow-up
          </span>
        )}
        {followup.draft_text && (
          <span className="rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-xs text-emerald-900">
            Follow-up provided
          </span>
        )}
      </div>
      {followup.reason && (
        <p className="mt-1 text-xs text-muted-foreground">{followup.reason}</p>
      )}
      <p className="mt-1 text-xs text-muted-foreground">
        Last activity: {formatDateTime(followup.last_activity)}
      </p>
    </div>
  )
}
