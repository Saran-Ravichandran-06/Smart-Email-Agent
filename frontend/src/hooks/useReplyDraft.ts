import { useCallback, useEffect, useState } from 'react'

import { generateReplyDraft, regenerateReplyDraft } from '@/api/replies'
import type { ReplyDraftResponse, ReplyTone } from '@/api/types'
import { errorMessage } from '@/lib/errors'
import { useAppStore } from '@/store/useAppStore'
import { useSettingsStore } from '@/store/useSettingsStore'

export function useReplyDraft(emailId: number | null) {
  const setLoading = useAppStore((s) => s.setLoading)
  const loading = useAppStore((s) => s.loading.reply)
  const defaultReplyTone = useSettingsStore((s) => s.defaultReplyTone)

  const [tone, setTone] = useState<ReplyTone>(defaultReplyTone)

  useEffect(() => {
    setTone(defaultReplyTone)
  }, [defaultReplyTone, emailId])
  const [draft, setDraft] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastResponse, setLastResponse] = useState<ReplyDraftResponse | null>(
    null,
  )

  const generate = useCallback(async () => {
    if (emailId === null) {
      return
    }
    setLoading('reply', true)
    setError(null)
    try {
      const response = await generateReplyDraft(emailId, { tone })
      setDraft(response.draft)
      setLastResponse(response)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading('reply', false)
    }
  }, [emailId, setLoading, tone])

  const regenerate = useCallback(async () => {
    if (emailId === null) {
      return
    }
    setLoading('reply', true)
    setError(null)
    try {
      const response = await regenerateReplyDraft(emailId, {
        tone,
        previous_draft: draft,
      })
      setDraft(response.draft)
      setLastResponse(response)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading('reply', false)
    }
  }, [draft, emailId, setLoading, tone])

  const reset = useCallback(() => {
    setDraft(null)
    setError(null)
    setLastResponse(null)
  }, [])

  return {
    tone,
    setTone,
    draft,
    setDraft,
    error,
    loading,
    lastResponse,
    generate,
    regenerate,
    reset,
  }
}
