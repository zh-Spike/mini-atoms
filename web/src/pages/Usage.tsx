import clsx from 'clsx'
import { useEffect, useState } from 'react'
import PageShell from '../components/PageShell'
import RunTraceDrawer from '../components/RunTrace'
import { Panel, StatCard, WindowSwitch } from '../components/Stats'
import { AgentTable, DailyRuns, DailyTokens, ModelTable, RunTable } from '../components/UsageTables'
import { api, ApiError, type UsageReport } from '../lib/api'
import { FullScreenSpinner } from '../lib/auth'
import { formatMs, formatPct, formatTokens } from '../lib/format'
import { useAuth } from '../lib/useAuth'

/** The account's own quota, consumption history and per-run traces. */
export default function Usage() {
  const { me } = useAuth()
  const [days, setDays] = useState(7)
  const [report, setReport] = useState<UsageReport | null>(null)
  const [error, setError] = useState('')
  const [traceId, setTraceId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api.usage(days).then(
      (r) => !cancelled && setReport(r),
      (err) => !cancelled && setError(err instanceof ApiError ? err.message : '加载失败'),
    )
    return () => {
      cancelled = true
    }
  }, [days])

  const nav = [
    { to: '/projects', label: '我的项目' },
    ...(me?.is_admin ? [{ to: '/admin', label: '运营' }] : []),
    { to: '/status', label: '服务状态' },
  ]

  if (error) return <p className="p-10 text-center text-sm text-red-600">{error}</p>
  if (!report) return <FullScreenSpinner />

  const { quota, totals } = report
  const usedPct = Math.min(1, quota.used / Math.max(1, quota.limit))

  return (
    <PageShell
      title="用量"
      subtitle="每一轮生成都会消耗 1 次额度（Race 按参赛模型数计）；点击任意一轮可查看每个智能体的耗时与 token"
      action={<WindowSwitch value={days} onChange={setDays} />}
      nav={nav}
    >
      <div className="mb-4 rounded-xl border border-zinc-200 bg-white p-4">
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-zinc-500">生成额度</span>
          <span>
            已用 <b>{quota.used}</b> / {quota.limit} 次 · 剩余 {quota.limit - quota.used} 次
          </span>
        </div>
        <div className="mt-2 h-2 rounded-full bg-zinc-100">
          <div
            className={clsx(
              'h-full rounded-full',
              usedPct > 0.9 ? 'bg-red-400' : usedPct > 0.7 ? 'bg-amber-400' : 'bg-violet-500',
            )}
            style={{ width: `${usedPct * 100}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label={`近 ${days} 天运行`} value={totals.runs} hint={`成功 ${totals.ok} · 失败 ${totals.error}`} />
        <StatCard
          label="成功率"
          value={formatPct(totals.success_rate)}
          tone={totals.success_rate !== null && totals.success_rate < 0.8 ? 'warn' : 'default'}
          hint={totals.aborted ? `${totals.aborted} 轮中途离开` : '不含中途离开的轮次'}
        />
        <StatCard
          label="Token 消耗"
          value={formatTokens(totals.tokens)}
          hint={`输入 ${formatTokens(totals.prompt_tokens)} · 输出 ${formatTokens(totals.completion_tokens)}`}
        />
        <StatCard
          label="耗时中位数"
          value={formatMs(totals.p50_duration_ms)}
          hint={`P95 ${formatMs(totals.p95_duration_ms)}`}
        />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Panel title="每日运行">
          <DailyRuns daily={report.daily} />
        </Panel>
        <Panel title="每日 Token">
          <DailyTokens daily={report.daily} />
        </Panel>
        <Panel title="按模型">
          <ModelTable rows={report.by_model} />
        </Panel>
        <Panel title="按智能体">
          <AgentTable rows={report.by_agent} />
        </Panel>
      </div>

      <Panel title="最近运行" className="mt-4">
        <RunTable runs={report.recent} onOpen={setTraceId} />
      </Panel>

      {traceId && <RunTraceDrawer runId={traceId} onClose={() => setTraceId(null)} />}
    </PageShell>
  )
}
