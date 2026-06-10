import { Inbox, ListTodo, RefreshCw, Settings } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type AppRoute = {
  path: string
  label: string
  icon: LucideIcon
  end?: boolean
}

export const appRoutes: AppRoute[] = [
  { path: '/', label: 'Inbox', icon: Inbox, end: true },
  { path: '/tasks', label: 'Tasks', icon: ListTodo },
  { path: '/follow-ups', label: 'Follow-Ups', icon: RefreshCw },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export function getRouteLabel(pathname: string): string {
  if (pathname.startsWith('/email/')) {
    if (pathname.endsWith('/reply')) {
      return 'Reply'
    }
    return 'Email'
  }
  const match = appRoutes.find((route) =>
    route.end ? pathname === route.path : pathname.startsWith(route.path),
  )
  return match?.label ?? 'Inbox'
}
