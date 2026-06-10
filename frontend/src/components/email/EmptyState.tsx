import CentralEmptyState from '@/components/ui/EmptyState'

type EmptyStateProps = {
  title: string
  description?: string
}

export default function EmptyState({ title, description }: EmptyStateProps) {
  return <CentralEmptyState title={title} description={description} />
}
