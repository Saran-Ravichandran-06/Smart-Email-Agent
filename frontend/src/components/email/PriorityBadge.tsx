import { priorityBadgeClass, priorityLabel } from '@/lib/priority'
import { cn } from '@/lib/utils'

type PriorityBadgeProps = {
  priority: string | null | undefined
  className?: string
}

export default function PriorityBadge({ priority, className }: PriorityBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide',
        priorityBadgeClass(priority),
        className,
      )}
    >
      {priorityLabel(priority)}
    </span>
  )
}
