import clsx from 'clsx'
import type { ReactNode } from 'react'
import type { RunStatus } from '../lib/api'
import { RUN_STATUS_LABEL } from '../lib/format'

export function StatCard({
  label,
  value,
  hint,
  tone = 'default',
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: 'default' | 'good' | 'warn' | 'bad'
}) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4">
      <div className="text-xs text-zinc-500">{label}</div>
      <div
        className={clsx(
          'mt-1 text-2xl font-semibold tracking-tight',
          tone === 'good' && 'text-emerald-600',
          tone === 'warn' && 'text-amber-600',
          tone === 'bad' && 'text-red-600',
        )}
      >
        {value}
      </div>
      {hint && <div className="mt-0.5 text-xs text-zinc-400">{hint}</div>}
    </div>
  )
}

export interface BarDatum {
  label: string
  /** Stacked segments, bottom first. */
  parts: { value: number; className: string }[]
  title: string
}

/** Minimal stacked bar chart; no chart library needed at these data sizes. */
export function Bars({ data, height = 120 }: { data: BarDatum[]; height?: number }) {
  const max = Math.max(1, ...data.map((d) => d.parts.reduce((s, p) => s + p.value, 0)))
  const every = Math.ceil(data.length / 8)
  return (
    <div>
      <div className="flex items-end gap-1" style={{ height }}>
        {data.map((d) => (
          <div
            key={d.label}
            title={d.title}
            className="flex h-full min-w-0 flex-1 flex-col-reverse rounded-sm bg-zinc-50"
          >
            {d.parts.map((p, i) => (
              <div
                key={i}
                className={clsx(p.className, i === d.parts.length - 1 && 'rounded-t-sm')}
                style={{ height: `${(p.value / max) * 100}%` }}
              />
            ))}
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-1 text-[10px] text-zinc-400">
        {data.map((d, i) => (
          <div key={d.label} className="min-w-0 flex-1 truncate text-center">
            {i % every === 0 ? d.label : ''}
          </div>
        ))}
      </div>
    </div>
  )
}

export function Panel({
  title,
  action,
  children,
  className,
}: {
  title: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={clsx('rounded-xl border border-zinc-200 bg-white p-4', className)}>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-medium">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

export function WindowSwitch({ value, onChange }: { value: number; onChange: (d: number) => void }) {
  return (
    <div className="flex items-center gap-0.5 rounded-lg bg-zinc-100 p-0.5 text-xs">
      {[7, 30].map((d) => (
        <button
          key={d}
          onClick={() => onChange(d)}
          className={clsx(
            'rounded-md px-2.5 py-1',
            value === d ? 'bg-white font-medium text-zinc-900 shadow-sm' : 'text-zinc-500',
          )}
        >
          近 {d} 天
        </button>
      ))}
    </div>
  )
}

export function RunStatusBadge({ status }: { status: RunStatus }) {
  return (
    <span
      className={clsx(
        'inline-flex rounded-full px-2 py-0.5 text-[11px] whitespace-nowrap',
        status === 'ok' && 'bg-emerald-50 text-emerald-700',
        status === 'error' && 'bg-red-50 text-red-700',
        status === 'aborted' && 'bg-zinc-100 text-zinc-600',
        status === 'running' && 'bg-sky-50 text-sky-700',
      )}
    >
      {RUN_STATUS_LABEL[status]}
    </span>
  )
}
