import { cn } from '@/lib/utils'

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn('animate-spin h-5 w-5 text-muted-foreground', className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-muted/60', className)}
    />
  )
}

export function ListSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-4 p-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex flex-col gap-2 rounded-lg border border-border/50 p-4">
          <div className="flex justify-between items-center">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-3 w-16" />
          </div>
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-5/6" />
          <div className="flex gap-2 mt-1">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function DetailSkeleton() {
  return (
    <div className="flex h-full flex-col space-y-6 p-6">
      {/* Header Area */}
      <div className="flex items-start justify-between border-b border-border pb-6">
        <div className="space-y-3 flex-1 max-w-xl">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-7 w-5/6" />
          <div className="flex items-center gap-3 mt-1">
            <Skeleton className="h-8 w-8 rounded-full" />
            <div className="space-y-1.5 flex-1">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-28" />
            </div>
          </div>
        </div>
        <Skeleton className="h-8 w-24 rounded-full" />
      </div>

      {/* Main Body */}
      <div className="flex-1 space-y-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-11/12" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-4/5" />
      </div>

      {/* Extracted Tasks or Summary Area */}
      <div className="rounded-lg border border-border bg-card/30 p-5 space-y-4">
        <Skeleton className="h-4 w-32" />
        <div className="space-y-3">
          <div className="flex items-start gap-2">
            <Skeleton className="h-4 w-4 rounded-sm mt-0.5" />
            <Skeleton className="h-4 w-5/6" />
          </div>
          <div className="flex items-start gap-2">
            <Skeleton className="h-4 w-4 rounded-sm mt-0.5" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        </div>
      </div>
    </div>
  )
}
