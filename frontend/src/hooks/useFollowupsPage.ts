import { useCallback, useEffect } from 'react'

import {
  fetchFollowups,
  generateFollowupDraft,
  resolveFollowup,
} from '@/api/followups'
import type { FollowUpResponse } from '@/api/types'
import { errorMessage } from '@/lib/errors'
import { useAppStore } from '@/store/useAppStore'
import { useFollowupStore } from '@/store/useFollowupStore'

let followupsInflight: Promise<void> | null = null

export function useFollowupsPage() {
  const followups = useFollowupStore((s) => s.followups)
  const followupsError = useFollowupStore((s) => s.followupsError)
  const loaded = useFollowupStore((s) => s.loaded)
  const actionError = useFollowupStore((s) => s.actionError)
  const draftingId = useFollowupStore((s) => s.draftingId)
  const resolvingId = useFollowupStore((s) => s.resolvingId)
  const setFollowups = useFollowupStore((s) => s.setFollowups)
  const setLoaded = useFollowupStore((s) => s.setLoaded)
  const setFollowupsError = useFollowupStore((s) => s.setFollowupsError)
  const setActionError = useFollowupStore((s) => s.setActionError)
  const setDraftingId = useFollowupStore((s) => s.setDraftingId)
  const setResolvingId = useFollowupStore((s) => s.setResolvingId)
  const updateFollowupInList = useFollowupStore((s) => s.updateFollowupInList)
  const removeFollowup = useFollowupStore((s) => s.removeFollowup)

  const setLoading = useAppStore((s) => s.setLoading)
  const loading = useAppStore((s) => s.loading.followups)

  const loadFollowups = useCallback(async (force = false) => {
    if (!force && loaded) {
      return
    }
    if (followupsInflight) {
      return followupsInflight
    }
    followupsInflight = (async () => {
    setLoading('followups', true)
    setFollowupsError(null)
    try {
      const data = await fetchFollowups()
      setFollowups(data)
      setLoaded(true)
    } catch (error) {
      setFollowupsError(errorMessage(error, 'Failed to load follow-ups.'))
      setFollowups([])
    } finally {
      setLoading('followups', false)
      followupsInflight = null
    }
    })()
    return followupsInflight
  }, [loaded, setFollowups, setFollowupsError, setLoaded, setLoading])

  useEffect(() => {
    void loadFollowups()
  }, [loadFollowups])

  const generateDraft = useCallback(
    async (followupId: number) => {
      setDraftingId(followupId)
      setActionError(null)
      try {
        const response = await generateFollowupDraft(followupId)
        const existing = useFollowupStore
          .getState()
          .followups.find((item) => item.id === followupId)
        if (existing) {
          const updated: FollowUpResponse = {
            ...existing,
            draft_text: response.draft,
          }
          updateFollowupInList(updated)
        }
      } catch (error) {
        setActionError(errorMessage(error, 'Failed to generate draft.'))
      } finally {
        setDraftingId(null)
      }
    },
    [setActionError, setDraftingId, updateFollowupInList],
  )

  const markResolved = useCallback(
    async (followupId: number) => {
      setResolvingId(followupId)
      setActionError(null)
      try {
        await resolveFollowup(followupId)
        removeFollowup(followupId)
      } catch (error) {
        setActionError(errorMessage(error, 'Failed to resolve follow-up.'))
      } finally {
        setResolvingId(null)
      }
    },
    [removeFollowup, setActionError, setResolvingId],
  )

  return {
    followups,
    loading,
    followupsError,
    actionError,
    draftingId,
    resolvingId,
    generateDraft,
    markResolved,
    reload: () => loadFollowups(true),
  }
}
