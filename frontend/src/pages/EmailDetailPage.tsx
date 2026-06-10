import { Navigate, useParams } from 'react-router-dom'

import EmailDetail from '@/components/email/EmailDetail'
import PageContainer from '@/components/layout/PageContainer'

export default function EmailDetailPage() {
  const { emailId } = useParams<{ emailId: string }>()
  const id = emailId ? Number.parseInt(emailId, 10) : Number.NaN

  if (Number.isNaN(id) || id <= 0) {
    return <Navigate to="/" replace />
  }

  return (
    <PageContainer>
      <EmailDetail emailId={id} />
    </PageContainer>
  )
}
