import { Link } from 'react-router-dom'

import type { ReplyTone } from '@/api/types'
import { Button } from '@/components/ui/button'
import ErrorState from '@/components/ui/ErrorState'
import { LoadingSpinner } from '@/components/ui/LoadingState'
import { useReplyDraft } from '@/hooks/useReplyDraft'
import { cn } from '@/lib/utils'

const TONES: { value: ReplyTone; label: string }[] = [
  { value: 'formal', label: 'Formal' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'friendly', label: 'Friendly' },
]

type ReplyBoxProps = {
  emailId: number
  showOpenLink?: boolean
}

export default function ReplyBox({ emailId, showOpenLink = false }: ReplyBoxProps) {
  const {
    tone,
    setTone,
    draft,
    error,
    loading,
    generate,
    regenerate,
  } = useReplyDraft(emailId)

  return (
    <section className="space-y-4 border-t border-border pt-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Reply draft</h3>
        {showOpenLink && (
          <Link
            to={`/email/${emailId}`}
            className="text-xs text-primary hover:underline"
          >
            Open full view
          </Link>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground text-[11px] uppercase font-semibold tracking-wider">Tone:</span>
        {TONES.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            disabled={loading}
            onClick={() => setTone(value)}
            className={cn(
              'rounded-md border px-2 py-0.5 text-xs font-medium cursor-pointer transition-colors',
              tone === value
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-background text-muted-foreground hover:bg-accent disabled:opacity-50 disabled:pointer-events-none',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          onClick={() => void generate()}
          disabled={loading}
          className="gap-1.5"
        >
          {loading && !draft && <LoadingSpinner className="h-3.5 w-3.5 text-primary-foreground" />}
          {loading && !draft ? 'Generating…' : 'Generate reply'}
        </Button>
        {draft && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void regenerate()}
            disabled={loading}
            className="gap-1.5"
          >
            {loading && <LoadingSpinner className="h-3.5 w-3.5" />}
            {loading ? 'Regenerating…' : 'Regenerate'}
          </Button>
        )}
      </div>

      {error && (
        <ErrorState
          title="Draft Generation Failed"
          message={error}
          onRetry={() => void generate()}
          retryText="Retry Draft Generation"
        />
      )}

      {loading && !draft && (
        <div className="rounded-md border border-border bg-card p-6 flex flex-col items-center justify-center space-y-2 py-8 animate-pulse">
          <LoadingSpinner className="h-6 w-6" />
          <p className="text-xs text-muted-foreground">Phi-3 AI is drafting your reply...</p>
        </div>
      )}

      {draft && (
        <div className={cn(
          "relative rounded-md border border-border bg-muted/20 p-4 transition-opacity",
          loading && "opacity-60"
        )}>
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/30 rounded-md">
              <div className="flex items-center gap-2 bg-card border border-border shadow-sm px-3 py-1.5 rounded-md">
                <LoadingSpinner className="h-4 w-4" />
                <span className="text-xs text-muted-foreground">Updating draft…</span>
              </div>
            </div>
          )}
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
            {draft}
          </pre>
        </div>
      )}

      {!draft && !loading && !error && (
        <p className="text-xs text-muted-foreground">
          Choose a tone and generate a draft. Replies are not sent automatically.
        </p>
      )}
    </section>
  )
}
