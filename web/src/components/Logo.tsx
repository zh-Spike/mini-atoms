import { Link } from 'react-router-dom'

export default function Logo({
  to = '/projects',
  compact = false,
}: {
  to?: string
  compact?: boolean
}) {
  return (
    <Link to={to} className="flex shrink-0 items-center gap-2 font-semibold tracking-tight">
      <img src="/favicon.svg" alt="" className="size-6" />
      <span className={compact ? 'hidden whitespace-nowrap sm:inline' : 'whitespace-nowrap'}>
        mini-atoms
      </span>
    </Link>
  )
}
