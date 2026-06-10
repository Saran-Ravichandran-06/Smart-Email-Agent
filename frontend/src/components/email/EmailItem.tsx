import type { EmailResponse } from '@/api/types'
import PriorityBadge from '@/components/email/PriorityBadge'
import { emailSnippet, formatTimestamp } from '@/lib/format'
import { cn } from '@/lib/utils'
import { useEmailStore } from '@/store/useEmailStore'

type EmailItemProps = {
  email: EmailResponse
  selected: boolean
  onSelect: (id: number) => void
}

export default function EmailItem({ email, selected, onSelect }: EmailItemProps) {
  const isUnread = !useEmailStore((s) => s.readEmailIds.includes(email.id))

  return (
    <button
      type="button"
      onClick={() => onSelect(email.id)}
      className={cn(
        'w-full border-b border-border px-3 py-3 text-left transition-colors hover:bg-accent/50',
        selected && 'bg-accent',
        isUnread && !selected && 'bg-muted/20',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span
          className={cn(
            'truncate text-sm',
            isUnread ? 'font-semibold text-foreground' : 'font-medium text-foreground',
          )}
        >
          {email.sender}
        </span>
        <span className="shrink-0 text-xs text-muted-foreground">
          {formatTimestamp(email.received_at)}
        </span>
      </div>
      <p
        className={cn(
          'mt-0.5 truncate text-sm',
          isUnread ? 'font-medium text-foreground' : 'text-foreground/90',
        )}
      >
        {email.subject || '(No subject)'}
      </p>
      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
        {emailSnippet(email.body)}
      </p>
      <div className="mt-2">
        <PriorityBadge priority={email.priority} />
      </div>
    </button>
  )
}
