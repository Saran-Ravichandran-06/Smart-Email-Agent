import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, Paperclip, Send } from 'lucide-react'
import { Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { fetchEmailById, fetchEmailCleaned } from '@/api/emails'
import { sendReply } from '@/api/replies'
import type { EmailResponse, ReplyTone } from '@/api/types'
import PageContainer from '@/components/layout/PageContainer'
import { Button } from '@/components/ui/button'
import ErrorState from '@/components/ui/ErrorState'
import { DetailSkeleton, LoadingSpinner } from '@/components/ui/LoadingState'
import { useReplyDraft } from '@/hooks/useReplyDraft'
import { errorMessage } from '@/lib/errors'
import { formatDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'

const TONES: { value: ReplyTone; label: string }[] = [
  { value: 'formal', label: 'Formal' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'friendly', label: 'Friendly' },
]

export default function ReplyPage() {
  const { emailId } = useParams<{ emailId: string }>()
  const id = emailId ? Number.parseInt(emailId, 10) : Number.NaN

  if (Number.isNaN(id) || id <= 0) {
    return <Navigate to="/" replace />
  }

  return (
    <PageContainer>
      <ReplyComposer emailId={id} />
    </PageContainer>
  )
}

type ReplyComposerProps = {
  emailId: number
}

function ReplyComposer({ emailId }: ReplyComposerProps) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [email, setEmail] = useState<EmailResponse | null>(null)
  const [body, setBody] = useState<string>('')
  const [pageLoading, setPageLoading] = useState(true)
  const [pageError, setPageError] = useState<string | null>(null)
  const [sendMessage, setSendMessage] = useState<string | null>(null)
  const [sending, setSending] = useState(false)

  const from = searchParams.get('from')

  const {
    tone,
    setTone,
    draft,
    setDraft,
    error,
    loading,
    generate,
    regenerate,
  } = useReplyDraft(emailId)

  const load = useCallback(async () => {
    setPageLoading(true)
    setPageError(null)
    try {
      const emailData = await fetchEmailById(emailId)
      const cleaned = await fetchEmailCleaned(emailId)
      setEmail(emailData)
      setBody(cleaned?.body_cleaned ?? emailData.body)
    } catch (err) {
      setPageError(errorMessage(err, 'Failed to load reply context.'))
    } finally {
      setPageLoading(false)
    }
  }, [emailId])

  useEffect(() => {
    void load()
  }, [load])



  const handleSend = async () => {
    const text = draft?.trim()
    if (!text) {
      setSendMessage('Generate or write a draft before sending.')
      return
    }
    setSending(true)
    setSendMessage(null)
    try {
      await sendReply(emailId, text)
      setSendMessage('Reply sent through Gmail.')
      navigate(from === 'followups' ? '/follow-ups' : '/')
    } catch (err) {
      setSendMessage(errorMessage(err, 'Failed to send the Gmail reply.'))
    } finally {
      setSending(false)
    }
  }

  if (pageLoading && !email) {
    return <DetailSkeleton />
  }

  if (pageError || !email) {
    return (
      <div className="mx-auto max-w-md py-12">
        <ErrorState
          title="Failed to load reply page"
          message={pageError ?? 'Email not found.'}
          onRetry={load}
          retryText="Retry"
        />
      </div>
    )
  }

  const isNoise = email.priority === 'noise'

  return (
    <div className="relative w-full">
      <div className="mb-4 xl:absolute xl:left-0 xl:top-0 xl:mb-0">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Back
        </button>
      </div>
      

      <div className="mx-auto w-full max-w-3xl">

      <header>

        <div className="mt-3 space-y-1 text-sm">
          <p>
            <span className="text-muted-foreground">To: </span>
            {email.sender}
          </p>
          <p>
            <span className="text-muted-foreground">Subject: </span>
            {email.subject || '(No subject)'}
          </p>
          <p className="text-xs text-muted-foreground">
            Received {formatDateTime(email.received_at)}
          </p>
        </div>
      </header>

      <div className="mt-6 space-y-6">
        <section>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Mail
          </h2>
          <div className="rounded-md border border-border bg-card p-4">
            <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
              {body}
            </pre>
          </div>
        </section>



        {isNoise ? (
          <p className="text-sm text-muted-foreground">
            Noise email: reply recommendations and send actions are skipped.
          </p>
        ) : (
        <section className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Tone:
            </span>
            {TONES.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                disabled={loading}
                onClick={() => setTone(value)}
                className={cn(
                  'rounded-md border px-2 py-0.5 text-xs font-medium transition-colors',
                  tone === value
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-background text-muted-foreground hover:bg-accent disabled:pointer-events-none disabled:opacity-50',
                )}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                onClick={() => void generate()}
                disabled={loading}
                className="gap-1.5"
              >
                {loading && !draft && <LoadingSpinner className="h-3.5 w-3.5 text-primary-foreground" />}
                {loading && !draft ? 'Generating...' : 'Generate reply'}
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
                  {loading ? 'Regenerating...' : 'Regenerate'}
                </Button>
              )}
            </div>

            <div className="flex items-center gap-1">
              <Button
                type="button"
                size="icon"
                variant="ghost"
                title="Attach file"
                onClick={() => setSendMessage('Attachments are not connected yet.')}
              >
                <Paperclip className="size-4" />
              </Button>
              <Button
                type="button"
                size="icon"
                title="Send email"
                disabled={sending}
                onClick={handleSend}
              >
                <Send className="size-4" />
              </Button>
            </div>
          </div>

          {error && (
            <ErrorState
              title="Draft generation failed"
              message={error}
              onRetry={() => void generate()}
              retryText="Retry"
            />
          )}

          <textarea
            value={draft ?? ''}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Generate a draft, then edit it here."
            className="min-h-44 w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-ring"
            style={{ minHeight: '240px' }}
          />

          {sendMessage && (
            <p className="text-xs text-muted-foreground">{sendMessage}</p>
          )}
        </section>
        )}
      </div>
    </div>
  </div>
  )
}
