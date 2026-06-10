import { AlertOctagon } from 'lucide-react'

import { Button } from '@/components/ui/button'

type ErrorStateProps = {
  title?: string
  message: string
  onRetry?: () => void
  retryText?: string
}

export default function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  retryText = 'Try again',
}: ErrorStateProps) {
  return (
    <div className="flex min-h-[220px] flex-col items-center justify-center rounded-lg border border-destructive/20 bg-destructive/5 p-6 text-center select-none">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-destructive/10 text-destructive mb-3">
        <AlertOctagon className="h-5 w-5" />
      </div>
      <h3 className="text-sm font-semibold text-foreground tracking-tight">
        {title}
      </h3>
      <p className="mt-1 max-w-sm text-xs leading-normal text-muted-foreground">
        {message}
      </p>
      {onRetry && (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onRetry}
          className="mt-4 border-destructive/20 text-destructive hover:bg-destructive/10 hover:text-destructive"
        >
          {retryText}
        </Button>
      )}
    </div>
  )
}
