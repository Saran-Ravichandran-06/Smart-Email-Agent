import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import OAuthRedirectHandler from '@/components/auth/OAuthRedirectHandler'
import AppLayout from '@/layouts/AppLayout'
import EmailDetailPage from '@/pages/EmailDetailPage'
import FollowupsPage from '@/pages/FollowupsPage'
import InboxPage from '@/pages/InboxPage'
import ReplyPage from '@/pages/ReplyPage'
import SettingsPage from '@/pages/SettingsPage'
import TasksPage from '@/pages/TasksPage'

export default function App() {
  return (
    <BrowserRouter>
      <OAuthRedirectHandler />
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<InboxPage />} />
          <Route path="email/:emailId" element={<EmailDetailPage />} />
          <Route path="email/:emailId/reply" element={<ReplyPage />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="follow-ups" element={<FollowupsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
