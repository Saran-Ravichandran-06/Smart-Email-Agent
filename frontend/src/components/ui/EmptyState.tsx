import { type LucideIcon, Inbox } from 'lucide-react'

import { Button } from '@/components/ui/button'

type EmptyStateProps = {
  title: string
  description?: string
  icon?: LucideIcon
  action?: {
    label: string
    onClick: () => void
    disabled?: boolean
    icon?: LucideIcon
  }
}

export default function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex min-h-[220px] flex-col items-center justify-center rounded-lg border border-dashed border-border/80 p-8 text-center select-none bg-card/20">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted mb-3 text-muted-foreground">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="text-sm font-semibold text-foreground tracking-tight">
        {title}
      </h3>
      {description && (
        <p className="mt-1 max-w-xs text-xs leading-normal text-muted-foreground">
          {description}
        </p>
      )}
      {action && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={action.disabled}
          onClick={action.onClick}
          className="mt-4 gap-1.5"
        >
          {action.icon && <action.icon className="h-3.5 w-3.5" />}
          {action.label}
        </Button>
      )}
    </div>
  )
}
