import clsx from 'clsx'
import type { AgentId } from '../lib/api'
import { AGENTS } from '../lib/agents'

export default function AgentAvatar({
  agent,
  size = 'md',
  pulse = false,
}: {
  agent: AgentId
  size?: 'sm' | 'md'
  pulse?: boolean
}) {
  const meta = AGENTS[agent]
  return (
    <span className="relative inline-flex shrink-0">
      <span
        className={clsx(
          'inline-flex items-center justify-center rounded-full font-semibold text-white',
          meta.color,
          size === 'sm' ? 'size-6 text-[11px]' : 'size-8 text-sm',
        )}
        title={`${meta.name} · ${meta.role}`}
      >
        {meta.name[0]}
      </span>
      {pulse && (
        <span className="absolute -right-0.5 -bottom-0.5 size-2.5 animate-pulse rounded-full border-2 border-white bg-green-500" />
      )}
    </span>
  )
}
