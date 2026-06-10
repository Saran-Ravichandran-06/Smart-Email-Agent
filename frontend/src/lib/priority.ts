export const PRIORITY_LABELS = ['urgent', 'important', 'low', 'noise'] as const

export type PriorityLabel = (typeof PRIORITY_LABELS)[number]

export type PriorityFilter = 'all' | 'urgent' | 'important' | 'unread'

export function normalizePriority(
  priority: string | null | undefined,
): PriorityLabel | null {
  if (!priority) {
    return null
  }
  const normalized = priority.toLowerCase()
  if (PRIORITY_LABELS.includes(normalized as PriorityLabel)) {
    return normalized as PriorityLabel
  }
  return null
}

export function priorityLabel(priority: string | null | undefined): string {
  const normalized = normalizePriority(priority)
  if (!normalized) {
    return 'Unclassified'
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}

export function priorityBadgeClass(priority: string | null | undefined): string {
  const normalized = normalizePriority(priority)
  switch (normalized) {
    case 'urgent':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'important':
      return 'bg-amber-100 text-amber-900 border-amber-200'
    case 'low':
      return 'bg-sky-100 text-sky-900 border-sky-200'
    case 'noise':
      return 'bg-muted text-muted-foreground border-border'
    default:
      return 'bg-secondary text-secondary-foreground border-border'
  }
}

export function apiPriorityParam(
  filter: PriorityFilter,
): string | undefined {
  if (filter === 'urgent' || filter === 'important') {
    return filter
  }
  return undefined
}
