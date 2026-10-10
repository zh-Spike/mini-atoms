import clsx from 'clsx'
import { Check } from 'lucide-react'
import type { AgentId } from '../lib/api'
import { AGENTS } from '../lib/agents'

/** Step indicator for the current run; edit runs skip Emma and Bob. */
export default function PipelineBar({
  steps,
  active,
  completed,
}: {
  steps: AgentId[]
  active: AgentId | null
  completed: AgentId[]
}) {
  return (
    <div className="flex items-center gap-1 text-xs">
      {steps.map((id, i) => {
        const done = completed.includes(id) && id !== active
        const isActive = id === active
        return (
          <div key={id} className="flex items-center gap-1">
            <span
              className={clsx(
                'flex items-center gap-1 rounded-full px-2 py-0.5 whitespace-nowrap',
                isActive && 'bg-violet-100 text-violet-700',
                done && 'text-emerald-600',
                !isActive && !done && 'text-zinc-400',
              )}
            >
              {done ? (
                <Check className="size-3" />
              ) : (
                <span
                  className={clsx(
                    'size-1.5 rounded-full',
                    isActive ? 'animate-pulse bg-violet-500' : 'bg-zinc-300',
                  )}
                />
              )}
              {AGENTS[id].role}
            </span>
            {i < steps.length - 1 && <span className="text-zinc-300">/</span>}
          </div>
        )
      })}
    </div>
  )
}
