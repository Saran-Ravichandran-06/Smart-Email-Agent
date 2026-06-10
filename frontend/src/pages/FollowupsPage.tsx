import { RefreshCw } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import FollowupList from '@/components/followups/FollowupList'
import PageContainer from '@/components/layout/PageContainer'
import { Button } from '@/components/ui/button'
import { useFollowupsPage } from '@/hooks/useFollowupsPage'
import { cn } from '@/lib/utils'

export default function FollowupsPage() {
  const navigate = useNavigate()
  const {
    followups,
    loading,
    followupsError,
    actionError,
    draftingId,
    resolvingId,
    markResolved,
    reload,
  } = useFollowupsPage()

  const openReplyPage = (followupId: number) => {
    const followup = followups.find((item) => item.id === followupId)
    if (followup?.latest_email_id) {
      navigate(`/email/${followup.latest_email_id}/reply?from=followups&followupId=${followup.id}`)
    }
  }

  return (
    <PageContainer
      title="Follow-Ups"
      description="Stale threads that may need a follow-up message."
    >
      <div className="mb-4 flex justify-end">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => void reload()}
          disabled={loading}
          className="gap-1"
        >
          <RefreshCw className={cn('size-3.5', loading && 'opacity-50')} />
          Refresh
        </Button>
      </div>

      <FollowupList
        followups={followups}
        loading={loading}
        error={followupsError}
        actionError={actionError}
        draftingId={draftingId}
        resolvingId={resolvingId}
        onGenerateDraft={openReplyPage}
        onResolve={(id) => void markResolved(id)}
        onRetry={() => void reload()}
      />
    </PageContainer>
  )
}
