import EmailList from '@/components/email/EmailList'
import EmailPreview from '@/components/email/EmailPreview'
import { useInboxEmails } from '@/hooks/useInbox'
import { useEmailStore } from '@/store/useEmailStore'

export default function InboxPage() {
  const { emails, loading, listError, syncInbox } = useInboxEmails()
  const selectedEmailId = useEmailStore((s) => s.selectedEmailId)
  const setSelectedEmailId = useEmailStore((s) => s.setSelectedEmailId)

  return (
    <div className="-m-6 h-[calc(100vh-6rem)] min-h-[480px] overflow-hidden">
      <div className="grid h-full min-h-0 overflow-hidden grid-cols-1 lg:grid-cols-[minmax(280px,360px)_1fr]">
        <EmailList
          emails={emails}
          selectedEmailId={selectedEmailId}
          loading={loading}
          error={listError}
          onSelect={setSelectedEmailId}
          onSync={() => void syncInbox()}
        />
        <EmailPreview />
      </div>
    </div>
  )
}
