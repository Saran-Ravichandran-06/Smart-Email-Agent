import { RefreshCw } from 'lucide-react'

import PageContainer from '@/components/layout/PageContainer'
import TaskList from '@/components/tasks/TaskList'
import { Button } from '@/components/ui/button'
import { useTasksPage } from '@/hooks/useTasksPage'
import type { TaskStatusFilter } from '@/store/useTaskStore'
import { cn } from '@/lib/utils'

const FILTERS: { value: TaskStatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
]

export default function TasksPage() {
  const {
    tasks,
    emailMap,
    statusFilter,
    setStatusFilter,
    loading,
    tasksError,
    updatingTaskId,
    markComplete,
    reload,
  } = useTasksPage()

  return (
    <PageContainer
      description="AI-extracted tasks from your emails."
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1">
          {FILTERS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => setStatusFilter(value)}
              className={cn(
                'rounded-md border px-2.5 py-1 text-xs font-medium',
                statusFilter === value
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-background text-muted-foreground hover:bg-accent',
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <Button
          type="button"
          className="gap-1 bg-yellow-500 hover:bg-yellow-600 text-yellow-950 border border-yellow-500"
          size="sm"
          onClick={() => void reload()}
          disabled={loading}
        >
          <RefreshCw className={cn('size-3.5', loading && 'opacity-50')} />
          Refresh
        </Button>
      </div>

      <TaskList
        tasks={tasks}
        emailMap={emailMap}
        loading={loading}
        error={tasksError}
        updatingTaskId={updatingTaskId}
        onMarkComplete={(id) => void markComplete(id)}
        onRetry={() => void reload()}
      />
    </PageContainer>
  )
}


