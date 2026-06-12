import { useState } from 'react'

import PageContainer from '@/components/layout/PageContainer'
import SettingsSection from '@/components/settings/SettingsSection'
import { Button } from '@/components/ui/button'
import { useSettingsPage } from '@/hooks/useSettingsPage'
import type { ReplyTone } from '@/api/types'
import { LoadingSpinner } from '@/components/ui/LoadingState'
import { cn } from '@/lib/utils'

const TONES: { value: ReplyTone; label: string }[] = [
  { value: 'formal', label: 'Formal' },
  { value: 'neutral', label: 'Neutral' },
  { value: 'friendly', label: 'Friendly' },
]

export default function SettingsPage() {
  const {
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
    reloadAuth,
  } = useSettingsPage()

  const [syncing, setSyncing] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const handleSync = async () => {
    setSyncing(true)
    await syncInbox()
    setSyncing(false)
  }

  const handleScan = async () => {
    setScanning(true)
    await rescanFollowups()
    setScanning(false)
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    await reloadAuth()
    setRefreshing(false)
  }

  return (
    <PageContainer
      description="Gmail connection, sync controls, and reply preferences."
    >
      <div className="mx-auto max-w-4xl space-y-4">
        {(actionMessage || actionError) && (
          <div
            className={cn(
              'rounded-md border px-4 py-3 text-sm transition-all',
              actionError
                ? 'border-destructive/30 bg-destructive/5 text-destructive'
                : 'border-border bg-muted/30 text-foreground',
            )}
          >
            {actionError ?? actionMessage}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SettingsSection
          title="Gmail connection"
          description="OAuth session used for inbox sync and email access."
        >
          {loading && !user && !authError ? (
            <div className="flex items-center gap-2 py-1">
              <LoadingSpinner className="h-4 w-4" />
              <p className="text-sm text-muted-foreground">Checking connection…</p>
            </div>
          ) : user ? (
            <div className="space-y-2 text-sm">
              <p>
                <span className="text-muted-foreground">Account: </span>
                {user.email}
                {user.name ? ` (${user.name})` : ''}
              </p>
              <p>
                <span className="text-muted-foreground">Gmail: </span>
                <span
                  className={cn(
                    'font-medium',
                    user.gmail_connected ? 'text-foreground' : 'text-destructive',
                  )}
                >
                  {user.gmail_connected ? 'Connected' : 'Not connected'}
                </span>
              </p>
            </div>
          ) : (
            <p className="text-sm text-destructive">
              {authError ?? 'Not signed in. Connect Gmail to use the app.'}
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={reconnectGmail}
              disabled={loading || syncing || scanning || refreshing}
            >
              {user?.gmail_connected ? 'Reconnect Gmail' : 'Connect Gmail'}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => void handleRefresh()}
              disabled={loading || syncing || scanning || refreshing}
              className="gap-1.5"
            >
              {refreshing && <LoadingSpinner className="h-3.5 w-3.5" />}
              Refresh status
            </Button>
          </div>
        </SettingsSection>

        <SettingsSection
          title="Inbox sync"
          description="Pull new messages from Gmail into the app."
        >
          <Button
            type="button"
            size="sm"
            onClick={() => void handleSync()}
            disabled={loading || syncing || scanning || refreshing}
            className="gap-1.5 bg-green-600 hover:bg-green-700 text-white"
          >
            {syncing && <LoadingSpinner className="h-3.5 w-3.5 text-primary-foreground" />}
            {syncing ? 'Syncing…' : 'Sync emails'}
          </Button>
        </SettingsSection>

        <SettingsSection
          title="Follow-up scan"
          description="Rescan threads for stale conversations needing follow-up."
        >
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void handleScan()}
            disabled={loading || syncing || scanning || refreshing}
            className="gap-1.5"
          >
            {scanning && <LoadingSpinner className="h-3.5 w-3.5" />}
            {scanning ? 'Scanning…' : 'Rescan inbox'}
          </Button>
        </SettingsSection>

        <SettingsSection
          title="Default reply tone"
          description="Used when generating reply drafts in the email detail view."
        >
          <div className="flex flex-wrap gap-2">
            {TONES.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                onClick={() => setDefaultReplyTone(value)}
                className={cn(
                  'rounded-md border px-2.5 py-1 text-xs font-medium cursor-pointer transition-colors',
                  defaultReplyTone === value
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-background text-muted-foreground hover:bg-accent',
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </SettingsSection>
        </div>
      </div>
    </PageContainer>
  )
}

