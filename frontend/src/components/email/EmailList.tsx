import { RefreshCw } from 'lucide-react'

import type { EmailResponse } from '@/api/types'
import EmailItem from '@/components/email/EmailItem'
import EmptyState from '@/components/email/EmptyState'
import { Button } from '@/components/ui/button'
import ErrorState from '@/components/ui/ErrorState'
import { ListSkeleton } from '@/components/ui/LoadingState'
import type { PriorityFilter } from '@/lib/priority'
import { cn } from '@/lib/utils'
import { useEmailStore } from '@/store/useEmailStore'

const FILTERS: { value: PriorityFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'urgent', label: 'Urgent' },
  { value: 'important', label: 'Important' },
  { value: 'unread', label: 'Unread' },
]

type EmailListProps = {
  emails: EmailResponse[]
  selectedEmailId: number | null
  loading: boolean
  error: string | null
  onSelect: (id: number) => void
  onSync: () => void
}

export default function EmailList({
  emails,
  selectedEmailId,
  loading,
  error,
  onSelect,
  onSync,
}: EmailListProps) {
  const priorityFilter = useEmailStore((s) => s.priorityFilter)
  const setPriorityFilter = useEmailStore((s) => s.setPriorityFilter)

  return (
    <div className="flex h-full min-h-0 flex-col border-r border-border bg-card">
      <div className="flex min-h-[108px] shrink-0 flex-col justify-center border-b border-border p-4">
        <div className="mb-3 flex items-center justify-end gap-2">
          <Button
            type="button"

            size="sm"
            onClick={onSync}
            disabled={loading}
            className="h-7 gap-1 px-2 text-xs bg-green-600 hover:bg-green-700 text-white border border-green-600"
          >
            <RefreshCw className={cn('size-3', loading && 'animate-spin')} />
            Sync
          </Button>
        </div>
        <div className="flex flex-wrap gap-1">
          {FILTERS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => setPriorityFilter(value)}
              className={cn(
                'rounded-md border px-2 py-0.5 text-xs font-medium cursor-pointer',
                priorityFilter === value
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-background text-muted-foreground hover:bg-accent',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading && emails.length === 0 && (
          <ListSkeleton count={3} />
        )}

        {error && (
          <div className="p-3">
            <ErrorState
              title="Sync / Load Error"
              message={error}
              onRetry={onSync}
              retryText="Retry Sync"
            />
          </div>
        )}

        {!loading && !error && emails.length === 0 && (
          <EmptyState
            title="No emails"
            description="Sync your Gmail inbox to load messages, or try a different filter."
          />
        )}

        {!loading && emails.map((email) => (
          <EmailItem
            key={email.id}
            email={email}
            selected={selectedEmailId === email.id}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  )
}


