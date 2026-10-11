import clsx from 'clsx'
import { useEffect, useState } from 'react'
import PageShell from '../components/PageShell'
import { Bars, Panel, StatCard } from '../components/Stats'
import { Empty } from '../components/UsageTables'
import { api, type ComponentState, type ServiceStatus } from '../lib/api'
import { FullScreenSpinner } from '../lib/auth'
import { formatDuration, formatMs, formatPct, formatTime } from '../lib/format'
import { useAuth } from '../lib/useAuth'

const REFRESH_MS = 30_000

const OVERALL = {
  operational: { text: '所有系统运行正常', className: 'border-emerald-200 bg-emerald-50 text-emerald-800', dot: 'bg-emerald-500' },
  degraded: { text: '部分服务性能下降', className: 'border-amber-200 bg-amber-50 text-amber-800', dot: 'bg-amber-500' },
  down: { text: '服务中断', className: 'border-red-200 bg-red-50 text-red-800', dot: 'bg-red-500' },
} as const

const COMPONENT_NAME = { app: '应用服务', database: '数据库', llm_gateway: '模型网关' } as const

const STATE = {
  up: { text: '正常', dot: 'bg-emerald-500' },
  down: { text: '不可用', dot: 'bg-red-500' },
  demo: { text: '演示模式', dot: 'bg-amber-400' },
} satisfies Record<ComponentState, { text: string; dot: string }>

/** Public status page: component health, 24h success rate and per-model availability. */
export default function Status() {
  const { me } = useAuth()
  const [data, setData] = useState<ServiceStatus | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const load = () =>
      api.status().then(
        (s) => {
          setData(s)
          setFailed(false)
        },
        () => setFailed(true),
      )
    void load()
    const timer = setInterval(load, REFRESH_MS)
    return () => clearInterval(timer)
  }, [])

  const nav = me
    ? [
        { to: '/projects', label: '我的项目' },
        { to: '/usage', label: '我的用量' },
      ]
    : [{ to: '/', label: '登录' }]

  if (!data && !failed) return <FullScreenSpinner />

  const overall = failed || !data ? OVERALL.down : OVERALL[data.status]
  return (
    <PageShell
      title="服务状态"
      subtitle={data ? `每 30 秒自动刷新 · 最近检查 ${formatTime(data.checked_at)}` : undefined}
      nav={nav}
    >
      <div className={clsx('flex items-center gap-3 rounded-xl border px-4 py-3', overall.className)}>
        <span className={clsx('size-2.5 rounded-full', overall.dot, 'animate-pulse')} />
        <span className="font-medium">{failed ? '无法连接到服务' : overall.text}</span>
      </div>

      {data && (
        <>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {data.components.map((c) => (
              <div key={c.name} className="rounded-xl border border-zinc-200 bg-white p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{COMPONENT_NAME[c.name]}</span>
                  <span className="flex items-center gap-1.5 text-xs text-zinc-600">
                    <span className={clsx('size-2 rounded-full', STATE[c.status].dot)} />
                    {STATE[c.status].text}
                  </span>
                </div>
                <div className="mt-1 text-xs text-zinc-400">
                  {c.latency_ms !== null ? `响应 ${formatMs(c.latency_ms)}` : c.detail || '\u00a0'}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="近 24 小时生成" value={data.runs_24h.runs} />
            <StatCard
              label="生成成功率"
              value={formatPct(data.runs_24h.success_rate)}
              tone={
                data.runs_24h.success_rate === null
                  ? 'default'
                  : data.runs_24h.success_rate >= 0.95
                    ? 'good'
                    : 'warn'
              }
            />
            <StatCard label="单轮耗时中位数" value={formatMs(data.runs_24h.p50_duration_ms)} />
            <StatCard label="已连续运行" value={formatDuration(data.uptime_s)} hint={`版本 ${data.version}`} />
          </div>

          <Panel title="近 24 小时（每小时，紫=成功，红=失败）" className="mt-4">
            <Bars
              height={80}
              data={data.hourly.map((h) => ({
                label: `${new Date(h.hour).getHours()}时`,
                title: `${formatTime(h.hour)}：成功 ${h.ok}，失败 ${h.error}`,
                parts: [
                  { value: h.ok, className: 'bg-violet-400' },
                  { value: h.error, className: 'bg-red-300' },
                ],
              }))}
            />
          </Panel>

          <Panel title="模型可用性（近 24 小时）" className="mt-4">
            {data.models_24h.length ? (
              <ul className="divide-y divide-zinc-100 text-sm">
                {data.models_24h.map((m) => (
                  <li key={m.model} className="flex items-center justify-between py-2">
                    <span className="flex items-center gap-2 font-mono text-xs">
                      <span
                        className={clsx(
                          'size-2 rounded-full',
                          (m.success_rate ?? 1) >= 0.95
                            ? 'bg-emerald-500'
                            : (m.success_rate ?? 1) >= 0.8
                              ? 'bg-amber-500'
                              : 'bg-red-500',
                        )}
                      />
                      {m.model}
                    </span>
                    <span className="text-xs text-zinc-500">
                      {m.calls} 次调用 · 成功率 {formatPct(m.success_rate)} · 平均首字{' '}
                      {formatMs(m.avg_ttft_ms)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty text="近 24 小时没有模型调用" />
            )}
          </Panel>
        </>
      )}
    </PageShell>
  )
}
