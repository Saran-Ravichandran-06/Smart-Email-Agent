import { useCallback, useEffect, useState } from 'react'

import { fetchAuthUser, getGoogleLoginUrl } from '@/api/auth'
import { syncEmails } from '@/api/emails'
import { scanFollowups } from '@/api/followups'
import type { EmailSyncResponse, FollowUpScanResponse } from '@/api/types'
import { errorMessage } from '@/lib/errors'
import { useAppStore } from '@/store/useAppStore'
import { useSettingsStore } from '@/store/useSettingsStore'

export function useSettingsPage() {
  const user = useSettingsStore((s) => s.user)
  const defaultReplyTone = useSettingsStore((s) => s.defaultReplyTone)
  const setUser = useSettingsStore((s) => s.setUser)
  const setDefaultReplyTone = useSettingsStore((s) => s.setDefaultReplyTone)

  const setLoading = useAppStore((s) => s.setLoading)
  const loading = useAppStore((s) => s.loading.settings)

  const [authError, setAuthError] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const loadAuth = useCallback(async () => {
    setLoading('settings', true)
    setAuthError(null)
    try {
      const authUser = await fetchAuthUser()
      setUser(authUser)
    } catch (error) {
      setAuthError(errorMessage(error, 'Not signed in.'))
      setUser(null)
    } finally {
      setLoading('settings', false)
    }
  }, [setLoading, setUser])

  useEffect(() => {
    void loadAuth()
  }, [loadAuth])

  const syncInbox = useCallback(async () => {
    setLoading('settings', true)
    setActionError(null)
    setActionMessage(null)
    try {
      const result: EmailSyncResponse = await syncEmails()
      setActionMessage(
        `Sync complete: ${result.synced} new, ${result.skipped} skipped.`,
      )
    } catch (error) {
      setActionError(errorMessage(error, 'Email sync failed.'))
    } finally {
      setLoading('settings', false)
    }
  }, [setLoading])

  const rescanFollowups = useCallback(async () => {
    setLoading('settings', true)
    setActionError(null)
    setActionMessage(null)
    try {
      const result: FollowUpScanResponse = await scanFollowups()
      setActionMessage(
        `Scan complete: ${result.created} created, ${result.updated} updated, ${result.scanned_threads} threads scanned.`,
      )
    } catch (error) {
      setActionError(errorMessage(error, 'Follow-up scan failed.'))
    } finally {
      setLoading('settings', false)
    }
  }, [setLoading])

  const reconnectGmail = useCallback(() => {
    window.location.href = getGoogleLoginUrl()
  }, [])

  return {
    user,
    authError,
    defaultReplyTone,
    setDefaultReplyTone,
    loading,
    actionMessage,
    actionError,
    syncInbox,
    rescanFollowups,
    reconnectGmail,
    reloadAuth: loadAuth,
  }
}
