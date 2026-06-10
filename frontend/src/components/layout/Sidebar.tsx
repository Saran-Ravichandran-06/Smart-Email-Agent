import { NavLink } from 'react-router-dom'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { appRoutes } from '@/lib/routes'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/store/useAppStore'

export default function Sidebar() {
  const collapsed = useAppStore((state) => state.sidebarCollapsed)
  const toggleSidebar = useAppStore((state) => state.toggleSidebar)

  return (
    <aside
      className={cn(
        'flex shrink-0 flex-col border-r border-border bg-card transition-[width] duration-200',
        collapsed ? 'w-16' : 'w-56',
      )}
    >
      <div
        className={cn(
          'flex h-[72px] items-center border-b border-border',
          collapsed ? 'justify-center px-2' : 'justify-between px-4',
        )}
      >
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Smart Email Agent
            </p>
            <p className="truncate text-sm font-semibold">Communication Hub</p>
          </div>
        )}
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <PanelLeftOpen className="size-4" />
          ) : (
            <PanelLeftClose className="size-4" />
          )}
        </Button>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-2">
        {appRoutes.map(({ path, label, icon: Icon, end }) => (
          <NavLink
            key={path}
            to={path}
            end={end}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              cn(
                'flex items-center rounded-md text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none',
                collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )
            }
          >
            <Icon className="size-4 shrink-0" />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
