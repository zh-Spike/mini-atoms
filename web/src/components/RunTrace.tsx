import clsx from 'clsx'
import { ChevronRight, Loader2, X } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { api, ApiError, type LLMCallTrace, type RunDetail } from '../lib/api'
import { AGENTS, laneName } from '../lib/agents'
import { formatMs, formatTime, formatTokens, RUN_MODE_LABEL } from '../lib/format'
import AgentAvatar from './AgentAvatar'
import { RunStatusBadge } from './Stats'

function stepLabel(c: LLMCallTrace): string {
  const parts: string[] = []
  if (c.lane !== null) parts.push(laneName(c.lane))
  if (c.step.endsWith('-fix-retry')) parts.push('修复轮 · 格式重试')
  else if (c.step.endsWith('-fix')) parts.push('修复轮')
  else if (c.step.endsWith('-retry')) parts.push('格式重试')
  return parts.join(' · ')
}

/** Side drawer with the step-by-step trace of one run. Admins also see the full prompts. */
export default function RunTraceDrawer({
  runId,
  admin = false,
  onClose,
}: {
  runId: string
  admin?: boolean
  onClose: () => void
}) {
  const [run, setRun] = useState<RunDetail | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(admin ? api.adminRun(runId) : api.getRun(runId)).then(
      (r) => !cancelled && setRun(r),
      (err) => !cancelled && setError(err instanceof ApiError ? err.message : '加载失败'),
    )
    return () => {
      cancelled = true
    }
  }, [runId, admin])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-zinc-900/30" onClick={onClose}>
      <div
        className="flex h-full w-full max-w-2xl flex-col bg-zinc-50 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-3">
          <div className="min-w-0">
            <div className="text-sm font-medium">本轮运行明细</div>
            {run && (
              <div className="truncate text-xs text-zinc-500">
                {run.project_title ?? '已删除的项目'}
                {run.username && ` · ${run.username}`} · {formatTime(run.created_at)}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-100"
            aria-label="关闭"
          >
            <X className="size-4" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto p-4">
          {error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : !run ? (
            <div className="flex justify-center pt-10">
              <Loader2 className="size-5 animate-spin text-violet-500" />
            </div>
          ) : (
            <RunTrace run={run} />
          )}
        </div>
      </div>
    </div>
  )
}

export function RunTrace({ run }: { run: RunDetail }) {
  const t0 = run.calls.length ? Date.parse(run.calls[0].started_at) : 0
  const span = Math.max(
    run.duration_ms,
    ...run.calls.map((c) => Date.parse(c.started_at) - t0 + c.duration_ms),
    1,
  )
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Fact label="状态">
          <RunStatusBadge status={run.status} />
        </Fact>
        <Fact label="类型">
          {RUN_MODE_LABEL[run.mode]}
          {run.race_lanes > 1 && ` · Race ×${run.race_lanes}`}
        </Fact>
        <Fact label="总耗时">{formatMs(run.duration_ms)}</Fact>
        <Fact label="Token（输入 / 输出）">
          {formatTokens(run.prompt_tokens)} / {formatTokens(run.completion_tokens)}
        </Fact>
      </div>

      {run.qa_ok !== null && (
        <div
          className={clsx(
            'rounded-lg border px-3 py-2 text-xs',
            run.qa_ok
              ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
              : 'border-amber-200 bg-amber-50 text-amber-800',
          )}
        >
          {run.qa_ok ? 'Quinn 静态检查通过' : 'Quinn 静态检查仍有问题：'}
          {!run.qa_ok && (
            <ul className="mt-1 list-disc pl-4">
              {run.qa_issues.map((i) => (
                <li key={i}>{i}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {run.error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {run.error}
        </div>
      )}

      <div>
        <div className="mb-2 text-xs text-zinc-500">
          模型调用 {run.calls.length} 次 · 横条表示每次调用在本轮中的起止时间
        </div>
        <ol className="space-y-2">
          {run.calls.map((c) => (
            <CallRow key={c.id} call={c} offset={Date.parse(c.started_at) - t0} span={span} />
          ))}
        </ol>
        {run.calls.length === 0 && (
          <p className="rounded-lg border border-dashed border-zinc-300 p-6 text-center text-xs text-zinc-400">
            这一轮没有记录到模型调用
          </p>
        )}
      </div>
    </div>
  )
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white px-3 py-2">
      <div className="text-[11px] text-zinc-400">{label}</div>
      <div className="mt-0.5 text-sm">{children}</div>
    </div>
  )
}

function CallRow({ call, offset, span }: { call: LLMCallTrace; offset: number; span: number }) {
  const [open, setOpen] = useState(false)
  const meta = AGENTS[call.agent]
  const extra = stepLabel(call)
  const ttftWidth = call.ttft_ms !== null ? Math.min(call.ttft_ms, call.duration_ms) : 0
  return (
    <li className="rounded-xl border border-zinc-200 bg-white">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-start gap-3 px-3 py-2.5 text-left"
      >
        <AgentAvatar agent={call.agent} size="sm" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 text-xs">
            <span className="font-medium text-zinc-900">{meta.name}</span>
            <span className="text-zinc-500">{meta.role}</span>
            {extra && <span className="text-violet-600">{extra}</span>}
            {call.model && <span className="font-mono text-zinc-400">{call.model}</span>}
            {call.status !== 'ok' && (
              <span className={call.status === 'error' ? 'text-red-600' : 'text-zinc-500'}>
                {call.status === 'error' ? '调用失败' : '已中断'}
              </span>
            )}
          </div>
          <div className="relative mt-1.5 h-1.5 rounded-full bg-zinc-100">
            <div
              className={clsx(
                'absolute inset-y-0 overflow-hidden rounded-full',
                call.status === 'error' ? 'bg-red-300' : 'bg-violet-400',
              )}
              style={{
                left: `${(offset / span) * 100}%`,
                width: `${Math.max(0.5, (call.duration_ms / span) * 100)}%`,
              }}
            >
              <div
                className="h-full bg-violet-200"
                style={{ width: `${(ttftWidth / Math.max(call.duration_ms, 1)) * 100}%` }}
              />
            </div>
          </div>
          <div className="mt-1 flex flex-wrap gap-x-3 text-[11px] text-zinc-500">
            <span>首字 {formatMs(call.ttft_ms)}</span>
            <span>耗时 {formatMs(call.duration_ms)}</span>
            <span>
              输入 {formatTokens(call.prompt_tokens)} · 输出 {formatTokens(call.completion_tokens)}
            </span>
          </div>
        </div>
        <ChevronRight
          className={clsx('mt-1 size-4 shrink-0 text-zinc-400 transition', open && 'rotate-90')}
        />
      </button>
      {open && (
        <div className="space-y-2 border-t border-zinc-100 px-3 py-2.5">
          {call.error && <Block title="错误" text={call.error} tone="error" />}
          {call.messages?.map((m, i) => (
            <Block key={i} title={`Prompt · ${m.role}`} text={m.content} />
          ))}
          <Block title="思考过程" text={call.thinking} empty="模型没有返回思考过程（快速模式下默认关闭）" />
          <Block title="输出" text={call.output} empty="无输出" />
        </div>
      )}
    </li>
  )
}

function Block({
  title,
  text,
  empty,
  tone,
}: {
  title: string
  text: string
  empty?: string
  tone?: 'error'
}) {
  const [full, setFull] = useState(false)
  const long = text.length > 1200
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px] text-zinc-500">
        <span>
          {title}
          {text && ` · ${text.length.toLocaleString()} 字符`}
        </span>
        {long && (
          <button onClick={() => setFull((f) => !f)} className="text-violet-600">
            {full ? '收起' : '展开全部'}
          </button>
        )}
      </div>
      {text ? (
        <pre
          className={clsx(
            'overflow-x-auto rounded-lg px-3 py-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap',
            tone === 'error' ? 'bg-red-50 text-red-700' : 'bg-zinc-50 text-zinc-700',
            !full && long && 'max-h-60 overflow-y-hidden',
          )}
        >
          {full || !long ? text : text.slice(0, 1200) + '\n…'}
        </pre>
      ) : (
        <p className="text-[11px] text-zinc-400 italic">{empty}</p>
      )}
    </div>
  )
}
