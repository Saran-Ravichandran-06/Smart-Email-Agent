import { useLocation } from 'react-router-dom'

import { getRouteLabel } from '@/lib/routes'
import { useAppStore } from '@/store/useAppStore'
import { LoadingSpinner } from '@/components/ui/LoadingState'

export default function Header() {
  const location = useLocation()
  const isLoading = useAppStore((state) => state.isLoading())

  return (
    <header className="flex h-[72px] shrink-0 items-center justify-between border-b border-border bg-background px-6 select-none">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">
          {getRouteLabel(location.pathname)}
        </h1>
        <p className="text-xs text-muted-foreground">
          Smart Email & Communication Agent
        </p>
      </div>
      {isLoading && (
        <div className="flex items-center gap-2 rounded-full border border-border bg-muted/40 px-2.5 py-1 text-xs font-medium text-muted-foreground transition-all duration-200">
          <LoadingSpinner className="h-3 w-3 text-muted-foreground" />
          <span>Syncing details</span>
        </div>
      )}
    </header>
  )
}
