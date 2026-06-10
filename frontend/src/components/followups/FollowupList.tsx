import { Clock, AlertTriangle } from 'lucide-react'

import type { FollowUpResponse } from '@/api/types'
import EmptyState from '@/components/ui/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import { ListSkeleton } from '@/components/ui/LoadingState'
import FollowupCard from '@/components/followups/FollowupCard'

type FollowupListProps = {
  followups: FollowUpResponse[]
  loading: boolean
  error: string | null
  actionError: string | null
  draftingId: number | null
  resolvingId: number | null
  onGenerateDraft: (id: number) => void
  onResolve: (id: number) => void
  onRetry?: () => void
}

export default function FollowupList({
  followups,
  loading,
  error,
  actionError,
  draftingId,
  resolvingId,
  onGenerateDraft,
  onResolve,
  onRetry,
}: FollowupListProps) {
  if (loading && followups.length === 0) {
    return (
      <div className="-mx-4">
        <ListSkeleton count={3} />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorState
        title="Failed to load follow-ups"
        message={error}
        onRetry={onRetry}
        retryText="Retry Loading Follow-Ups"
      />
    )
  }

  if (followups.length === 0 && !actionError) {
    return (
      <EmptyState
        title="No follow-ups flagged"
        description="Threads that are waiting for response or need attention will be listed here. You can scan for stale threads from Settings."
        icon={Clock}
      />
    )
  }

  return (
    <div className="space-y-4">
      {actionError && (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive select-none animate-shake">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <p className="font-medium text-xs">{actionError}</p>
        </div>
      )}
      <ul className="space-y-3">
        {followups.map((followup) => (
          <li key={followup.id}>
            <FollowupCard
              followup={followup}
              onGenerateDraft={onGenerateDraft}
              onResolve={onResolve}
              drafting={draftingId === followup.id}
              resolving={resolvingId === followup.id}
            />
          </li>
        ))}
      </ul>
    </div>
  )
}

