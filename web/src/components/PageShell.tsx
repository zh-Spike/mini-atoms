import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import Logo from './Logo'

export default function PageShell({
  title,
  subtitle,
  action,
  nav,
  children,
}: {
  title: string
  subtitle?: ReactNode
  action?: ReactNode
  nav?: { to: string; label: string }[]
  children: ReactNode
}) {
  return (
    <div className="h-full overflow-y-auto bg-zinc-50">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <Logo />
          <nav className="flex items-center gap-4 text-sm text-zinc-500">
            {nav?.map((n) => (
              <Link key={n.to} to={n.to} className="hover:text-zinc-900">
                {n.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
            {subtitle && <p className="mt-1 text-sm text-zinc-500">{subtitle}</p>}
          </div>
          {action}
        </div>
        {children}
      </main>
    </div>
  )
}
