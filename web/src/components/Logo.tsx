import { Link } from 'react-router-dom'

export default function Logo({ to = '/projects' }: { to?: string }) {
  return (
    <Link to={to} className="flex items-center gap-2 font-semibold tracking-tight">
      <img src="/favicon.svg" alt="" className="size-6" />
      <span>mini-atoms</span>
    </Link>
  )
}
