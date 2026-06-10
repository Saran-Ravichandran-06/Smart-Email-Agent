import type { ReactNode } from 'react'

type SettingsSectionProps = {
  title: string
  description?: string
  children: ReactNode
}

export default function SettingsSection({
  title,
  description,
  children,
}: SettingsSectionProps) {
  return (
    <section className="rounded-lg border border-border bg-card p-5">
      <h2 className="text-sm font-semibold">{title}</h2>
      {description && (
        <p className="mt-1 text-xs text-muted-foreground">{description}</p>
      )}
      <div className="mt-4">{children}</div>
    </section>
  )
}
