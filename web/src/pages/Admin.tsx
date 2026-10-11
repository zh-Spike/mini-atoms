import { RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import PageShell from '../components/PageShell'
import RunTraceDrawer from '../components/RunTrace'
import { Panel, StatCard, WindowSwitch } from '../components/Stats'
import {
  AgentTable,
  DailyRuns,
  DailyTokens,
  Empty,
  ModelTable,
  RunTable,
} from '../components/UsageTables'
import { api, ApiError, type AdminOverview, type AdminRunPage } from '../lib/api'
import { FullScreenSpinner } from '../lib/auth'
import { formatMs, formatPct, formatTokens } from '../lib/format'
import { useAuth } from '../lib/useAuth'

const NAV = [
  { to: '/projects', label: '我的项目' },
  { to: '/usage', label: '我的用量' },
  { to: '/status', label: '服务状态' },
]

const SELECT = 'rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs'

/** Operations dashboard: product usage, model health, quality and full prompt traces. */
export default function Admin() {
  const { me } = useAuth()
  const [days, setDays] = useState(7)
  const [data, setData] = useState<AdminOverview | null>(null)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  const [traceId, setTraceId] = useState<string | null>(null)

  useEffect(() => {
    if (!me?.is_admin) return
    let cancelled = false
    api.adminOverview(days).then(
      (d) => !cancelled && setData(d),
      (err) => !cancelled && setError(err instanceof ApiError ? err.message : '加载失败'),
    )
    return () => {
      cancelled = true
    }
  }, [days, reload, me?.is_admin])

  if (!me?.is_admin) {
    return (
      <PageShell title="运营" nav={NAV}>
        <p className="rounded-xl border border-dashed border-zinc-300 p-10 text-center text-sm text-zinc-500">
          需要管理员权限。管理员账号通过服务端配置 <code>ADMIN_USERNAMES</code> 指定。
        </p>
      </PageShell>
    )
  }
  if (error) return <p className="p-10 text-center text-sm text-red-600">{error}</p>
  if (!data) return <FullScreenSpinner />

  const { totals, users, quality, shares } = data
  return (
    <PageShell
      title="运营"
      subtitle="产品使用、模型健康度与生成质量；点击运行记录可查看完整 prompt、思考过程和输出"
      nav={NAV}
      action={
        <div className="flex items-center gap-2">
          <button
            onClick={() => setReload((n) => n + 1)}
            className="rounded-md p-1.5 text-zinc-500 hover:bg-zinc-200"
            aria-label="刷新"
          >
            <RefreshCw className="size-4" />
          </button>
          <WindowSwitch value={days} onChange={setDays} />
        </div>
      }
    >
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <StatCard label="用户" value={users.total} hint={`新增 ${users.new} · 活跃 ${users.active}`} />
        <StatCard label="项目" value={data.projects.total} hint={`新增 ${data.projects.new}`} />
        <StatCard
          label="运行"
          value={totals.runs}
          hint={`失败 ${totals.error} · 中断 ${totals.aborted}`}
        />
        <StatCard
          label="成功率"
          value={formatPct(totals.success_rate)}
          tone={
            totals.success_rate === null
              ? 'default'
              : totals.success_rate >= 0.95
                ? 'good'
                : totals.success_rate >= 0.8
                  ? 'warn'
                  : 'bad'
          }
        />
        <StatCard
          label="耗时 P50 / P95"
          value={formatMs(totals.p50_duration_ms)}
          hint={`P95 ${formatMs(totals.p95_duration_ms)}`}
        />
        <StatCard
          label="Token"
          value={formatTokens(totals.tokens)}
          hint={`单轮平均 ${formatTokens(Math.round(totals.tokens / Math.max(1, totals.runs)))}`}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Panel title="每日运行（紫=成功，红=失败，灰=中断）">
          <DailyRuns daily={data.daily} />
        </Panel>
        <Panel title="每日 Token">
          <DailyTokens daily={data.daily} />
        </Panel>
      </div>

      <Panel title="模型健康度" className="mt-4">
        <ModelTable rows={data.by_model} />
      </Panel>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Panel title="智能体 Token 占比">
          <AgentTable rows={data.by_agent} />
        </Panel>
        <Panel title="生成质量">
          <dl className="grid grid-cols-2 gap-3 text-xs">
            <Metric label="QA 最终通过率" value={formatPct(quality.qa_pass_rate)} />
            <Metric label="需要修复轮的比例" value={formatPct(quality.fix_rate)} />
            <Metric label="Race 次数" value={quality.race_runs} />
            <Metric label="Race 方案被采用" value={quality.race_adopted} />
          </dl>
        </Panel>
        <Panel title="活跃用户 Top 5">
          {data.top_users.length ? (
            <ul className="space-y-1.5 text-xs">
              {data.top_users.map((u) => (
                <li key={u.username} className="flex justify-between">
                  <span>{u.username}</span>
                  <span className="text-zinc-500">
                    {u.runs} 轮 · {formatTokens(u.tokens)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <Empty />
          )}
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Panel title="额度预警（已用 80% 以上）">
          {data.quota_alerts.length ? (
            <ul className="space-y-1.5 text-xs">
              {data.quota_alerts.map((u) => (
                <li key={u.username} className="flex justify-between">
                  <span>{u.username}</span>
                  <span className={u.used >= u.limit ? 'text-red-600' : 'text-amber-600'}>
                    {u.used} / {u.limit}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <Empty text="没有接近上限的账号" />
          )}
        </Panel>
        <Panel title="邀请码">
          <ul className="space-y-1.5 text-xs">
            {data.invites.map((i) => (
              <li key={i.code} className="flex justify-between">
                <span className={i.enabled ? 'font-mono' : 'font-mono text-zinc-400 line-through'}>
                  {i.code}
                </span>
                <span className="text-zinc-500">
                  {i.used} / {i.max}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="发布分享">
          <div className="mb-2 text-xs text-zinc-500">
            {shares.total} 个已发布应用 · 累计浏览 {shares.views_total} · 近 {days} 天 {shares.views_window}
          </div>
          {shares.top.length ? (
            <ul className="space-y-1.5 text-xs">
              {shares.top.map((s) => (
                <li key={s.slug} className="flex justify-between gap-2">
                  <a
                    href={`/s/${s.slug}`}
                    target="_blank"
                    rel="noreferrer"
                    className="truncate text-violet-700 hover:underline"
                  >
                    {s.title ?? s.slug}
                  </a>
                  <span className="shrink-0 text-zinc-500">{s.views} 次</span>
                </li>
              ))}
            </ul>
          ) : (
            <Empty />
          )}
        </Panel>
      </div>

      <RunList onOpen={setTraceId} />

      {traceId && <RunTraceDrawer runId={traceId} admin onClose={() => setTraceId(null)} />}
    </PageShell>
  )
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-zinc-50 p-3">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="mt-1 text-lg font-semibold">{value}</dd>
    </div>
  )
}

function RunList({ onOpen }: { onOpen: (id: string) => void }) {
  const [status, setStatus] = useState('')
  const [model, setModel] = useState('')
  const [username, setUsername] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState<AdminRunPage | null>(null)

  const load = useCallback(
    () => api.adminRuns({ status, model, username, page }).then(setData),
    [status, model, username, page],
  )
  useEffect(() => {
    void load()
  }, [load])

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1
  return (
    <Panel
      title={`运行记录${data ? `（${data.total}）` : ''}`}
      className="mt-4"
      action={
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value)
              setPage(1)
            }}
            className={SELECT}
          >
            <option value="">全部状态</option>
            <option value="ok">成功</option>
            <option value="error">失败</option>
            <option value="aborted">中断</option>
            <option value="running">进行中</option>
          </select>
          <select
            value={model}
            onChange={(e) => {
              setModel(e.target.value)
              setPage(1)
            }}
            className={SELECT}
          >
            <option value="">全部模型</option>
            {data?.models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <input
            value={username}
            onChange={(e) => {
              setUsername(e.target.value)
              setPage(1)
            }}
            placeholder="用户名"
            className={`${SELECT} w-28`}
          />
        </div>
      }
    >
      {data ? <RunTable runs={data.items} showUser onOpen={onOpen} /> : <Empty text="加载中…" />}
      {pages > 1 && (
        <div className="mt-3 flex items-center justify-end gap-2 text-xs text-zinc-500">
          <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="disabled:opacity-40">
            上一页
          </button>
          <span>
            {page} / {pages}
          </span>
          <button
            disabled={page >= pages}
            onClick={() => setPage(page + 1)}
            className="disabled:opacity-40"
          >
            下一页
          </button>
        </div>
      )}
    </Panel>
  )
}
