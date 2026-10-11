import clsx from 'clsx'
import { Gauge } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { Me } from '../lib/api'

/** Remaining generations, always visible in the header; opens the usage page. */
export default function QuotaBadge({ me, className }: { me: Me | null; className?: string }) {
  if (!me) return null
  const left = me.generation_limit - me.generations_used
  const low = left <= Math.max(2, me.generation_limit * 0.1)
  return (
    <Link
      to="/usage"
      title="查看用量明细"
      className={clsx(
        'items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs whitespace-nowrap',
        low
          ? 'border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100'
          : 'border-zinc-200 bg-white text-zinc-600 hover:border-violet-300 hover:text-violet-700',
        className ?? 'flex',
      )}
    >
      <Gauge className="size-3.5" />
      剩余 <b className="font-semibold">{left}</b> / {me.generation_limit} 次
    </Link>
  )
}
