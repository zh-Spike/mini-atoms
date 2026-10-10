import clsx from 'clsx'
import { Check, Swords } from 'lucide-react'
import type { ModelsInfo } from '../lib/api'
import { initialRaceModels, rememberRaceModels } from '../lib/models'

interface ToggleProps {
  info: ModelsInfo | null
  value: string[] | null
  onChange: (models: string[] | null) => void
  disabled?: boolean
}

/** Turns Race on with the last line-up of models, or off (`null`). */
export function RaceToggle({ info, value, onChange, disabled }: ToggleProps) {
  const on = value !== null
  return (
    <button
      type="button"
      disabled={disabled || !info || info.race_models.length < 2}
      onClick={() => onChange(on || !info ? null : initialRaceModels(info))}
      title="多个模型基于同一份 PRD 并行写代码，生成后对比预览、择优采用。仅在新建或推倒重做时生效，每个参赛模型消耗 1 次额度"
      className={clsx(
        'flex items-center gap-1 rounded-full px-2.5 py-1 text-xs whitespace-nowrap disabled:opacity-40',
        on
          ? 'bg-violet-600 text-white'
          : 'bg-zinc-100 text-zinc-500 hover:bg-violet-50 hover:text-violet-700',
      )}
    >
      <Swords className="size-3.5" /> Race{on && ` ×${value.length}`}
    </button>
  )
}

/** Chips for picking 2..max models that compete in a race. */
export function RaceModelPicker({
  info,
  value,
  onChange,
}: {
  info: ModelsInfo
  value: string[]
  onChange: (models: string[]) => void
}) {
  function toggle(model: string) {
    const next = value.includes(model) ? value.filter((m) => m !== model) : [...value, model]
    if (next.length < 2 || next.length > info.max_race_lanes) return
    rememberRaceModels(next)
    onChange(next)
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5 px-1 pb-2">
      <span className="text-[11px] text-zinc-400">
        参赛模型（{value.length}/{info.max_race_lanes}，消耗 {value.length} 次额度）
      </span>
      {info.race_models.map((m) => {
        const picked = value.includes(m)
        const blocked = picked ? value.length <= 2 : value.length >= info.max_race_lanes
        return (
          <button
            key={m}
            type="button"
            onClick={() => toggle(m)}
            title={blocked ? (picked ? '至少保留 2 个模型' : `最多 ${info.max_race_lanes} 个模型`) : m}
            className={clsx(
              'flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[11px]',
              picked
                ? 'border-violet-300 bg-violet-50 text-violet-700'
                : 'border-zinc-200 text-zinc-500 hover:border-violet-200',
              blocked && !picked && 'cursor-not-allowed opacity-50',
            )}
          >
            {picked && <Check className="size-3" />}
            {m}
          </button>
        )
      })}
    </div>
  )
}
