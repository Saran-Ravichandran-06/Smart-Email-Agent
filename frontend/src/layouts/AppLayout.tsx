import { Outlet } from 'react-router-dom'

import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'

export default function AppLayout() {
  return (
    <div className="flex h-svh overflow-hidden bg-background">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 relative">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
