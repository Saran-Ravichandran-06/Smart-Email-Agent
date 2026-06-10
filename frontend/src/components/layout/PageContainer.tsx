import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

type PageContainerProps = {
  title?: string
  description?: string
  children: ReactNode
  className?: string
}

export default function PageContainer({
  title,
  description,
  children,
  className,
}: PageContainerProps) {
  return (
    <div className={cn('mx-auto w-full max-w-6xl', className)}>
      {(title || description) && (
        <div className="mb-6">
          {title && (
            <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
          )}
          {description && (
            <p className="mt-1 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      )}
      {children}
    </div>
  )
}
