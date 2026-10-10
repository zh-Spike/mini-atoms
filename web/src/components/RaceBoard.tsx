import clsx from 'clsx'
import { AlertTriangle, Check, CheckCircle2, Flag, Loader2, Trophy } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { LaneState } from '../hooks/useAgentRun'
import type { Version } from '../lib/api'
import { AGENTS, laneName } from '../lib/agents'

export interface RaceCandidate {
  lane: number
  label: string
  version: Version
}

/** Side-by-side view of the lanes while they are coding. */
export function RaceLive({ lanes }: { lanes: LaneState[] }) {
  return (
    <div
      className="grid h-full gap-px bg-zinc-800"
      style={{ gridTemplateColumns: `repeat(${lanes.length}, minmax(0, 1fr))` }}
    >
      {lanes.map((lane, i) => (
        <LaneColumn key={i} index={i} lane={lane} />
      ))}
    </div>
  )
}

function LaneColumn({ index, lane }: { index: number; lane: LaneState }) {
  const preRef = useRef<HTMLPreElement>(null)
  const code = lane.currentFile ? (lane.files[lane.currentFile] ?? '') : ''
  useEffect(() => {
    const el = preRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [code])

  const status = lane.error
    ? '出错了'
    : lane.finished
      ? lane.qaOk === false
        ? '完成（检查有问题）'
        : '完成'
      : lane.agent
        ? AGENTS[lane.agent].working
        : '等待开始'

  return (
    <div className="flex min-w-0 flex-col bg-zinc-950 text-zinc-100">
      <div className="flex items-center justify-between gap-2 border-b border-zinc-800 px-3 py-2">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-sm font-medium">
            <Flag className="size-3.5 text-violet-400" /> {laneName(index)}
          </div>
          <div className="truncate text-xs text-zinc-500">{lane.label}</div>
        </div>
        <span
          className={clsx(
            'flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs',
            lane.error
              ? 'bg-red-500/15 text-red-300'
              : lane.finished
                ? 'bg-emerald-500/15 text-emerald-300'
                : 'bg-sky-500/15 text-sky-300',
          )}
        >
          {lane.error ? (
            <AlertTriangle className="size-3" />
          ) : lane.finished ? (
            <CheckCircle2 className="size-3" />
          ) : (
            <Loader2 className="size-3 animate-spin" />
          )}
          {status}
        </span>
      </div>
      <ul className="max-h-32 shrink-0 space-y-0.5 overflow-y-auto border-b border-zinc-800 p-2">
        {Object.keys(lane.files).map((path) => (
          <li
            key={path}
            className={clsx(
              'flex items-center gap-2 rounded px-2 py-0.5 font-mono text-xs',
              path === lane.currentFile && !lane.finished ? 'bg-zinc-800 text-white' : 'text-zinc-400',
            )}
          >
            {lane.doneFiles.includes(path) ? (
              <Check className="size-3.5 shrink-0 text-emerald-400" />
            ) : (
              <Loader2 className="size-3.5 shrink-0 animate-spin text-sky-400" />
            )}
            <span className="truncate">{path}</span>
          </li>
        ))}
        {Object.keys(lane.files).length === 0 && (
          <li className="px-2 py-0.5 text-xs text-zinc-500">{lane.error ?? '等待工程师开工…'}</li>
        )}
      </ul>
      <pre
        ref={preRef}
        className="min-h-0 flex-1 overflow-auto p-3 font-mono text-xs leading-relaxed text-zinc-300"
      >
        {code ||
          (lane.thinking && !lane.finished && (
            <span className="text-zinc-500 italic">
              {AGENTS[lane.agent ?? 'alex'].name} 正在思考：{lane.thinking}
            </span>
          ))}
        {!lane.finished && (
          <span className="inline-block h-3.5 w-1.5 translate-y-0.5 animate-pulse bg-sky-400" />
        )}
      </pre>
    </div>
  )
}

/** Tabs over finished candidates plus an "adopt" action; the preview itself is rendered below. */
export function RacePicker({
  candidates,
  selected,
  onSelect,
  onAdopt,
  onDismiss,
}: {
  candidates: RaceCandidate[]
  selected: number
  onSelect: (i: number) => void
  onAdopt: () => void
  onDismiss: () => void
}) {
  return (
    <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-violet-200 bg-violet-50 px-3 py-2">
      <div className="flex items-center gap-2">
        <Trophy className="size-4 text-violet-600" />
        <span className="text-xs text-violet-900">选出你更喜欢的方案：</span>
        <div className="flex gap-1">
          {candidates.map((c, i) => (
            <button
              key={c.version.id}
              onClick={() => onSelect(i)}
              title={c.label}
              className={clsx(
                'rounded-md px-2.5 py-1 text-xs whitespace-nowrap',
                i === selected
                  ? 'bg-violet-600 text-white'
                  : 'bg-white text-violet-700 ring-1 ring-violet-200 hover:bg-violet-100',
              )}
            >
              {laneName(c.lane)} · v{c.version.number}
            </button>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button onClick={onDismiss} className="text-xs text-zinc-500 hover:text-zinc-800">
          稍后再选
        </button>
        <button
          onClick={onAdopt}
          className="flex items-center gap-1 rounded-md bg-violet-600 px-2.5 py-1 text-xs whitespace-nowrap text-white hover:bg-violet-700"
        >
          <Check className="size-3.5" /> 采用{laneName(candidates[selected].lane)}
        </button>
      </div>
    </div>
  )
}
