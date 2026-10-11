import type { AgentTotals, DailyPoint, ModelUsage, RunSummary } from '../lib/api'
import { AGENTS } from '../lib/agents'
import {
  formatMs,
  formatPct,
  formatTime,
  formatTokens,
  RUN_MODE_LABEL,
  shortDate,
} from '../lib/format'
import AgentAvatar from './AgentAvatar'
import { Bars, RunStatusBadge } from './Stats'

const TH = 'px-2 py-1.5 text-left font-normal text-zinc-400'
const TD = 'px-2 py-1.5'

export function DailyRuns({ daily }: { daily: DailyPoint[] }) {
  return (
    <Bars
      data={daily.map((d) => ({
        label: shortDate(d.date),
        title: `${d.date}：${d.runs} 轮（成功 ${d.ok}，失败 ${d.error}），${d.tokens.toLocaleString()} tokens`,
        parts: [
          { value: d.ok, className: 'bg-violet-400' },
          { value: d.error, className: 'bg-red-300' },
          { value: d.runs - d.ok - d.error, className: 'bg-zinc-300' },
        ],
      }))}
    />
  )
}

export function DailyTokens({ daily }: { daily: DailyPoint[] }) {
  return (
    <Bars
      data={daily.map((d) => ({
        label: shortDate(d.date),
        title: `${d.date}：${d.tokens.toLocaleString()} tokens`,
        parts: [{ value: d.tokens, className: 'bg-sky-400' }],
      }))}
    />
  )
}

export function ModelTable({ rows }: { rows: ModelUsage[] }) {
  if (!rows.length) return <Empty />
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className={TH}>模型</th>
            <th className={TH}>调用</th>
            <th className={TH}>成功率</th>
            <th className={TH}>平均首字</th>
            <th className={TH}>P95 首字</th>
            <th className={TH}>平均耗时</th>
            <th className={TH}>Token</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((m) => (
            <tr key={m.model} className="border-t border-zinc-100">
              <td className={`${TD} font-mono`}>{m.model}</td>
              <td className={TD}>{m.calls}</td>
              <td className={TD}>
                <span className={m.errors ? 'text-amber-700' : ''}>{formatPct(m.success_rate)}</span>
                {m.errors > 0 && <span className="text-zinc-400"> （失败 {m.errors}）</span>}
              </td>
              <td className={TD}>{formatMs(m.avg_ttft_ms)}</td>
              <td className={TD}>{formatMs(m.p95_ttft_ms)}</td>
              <td className={TD}>{formatMs(m.avg_duration_ms)}</td>
              <td className={TD}>{formatTokens(m.tokens)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function AgentTable({ rows }: { rows: AgentTotals[] }) {
  if (!rows.length) return <Empty />
  const total = Math.max(1, rows.reduce((s, r) => s + r.tokens, 0))
  return (
    <ul className="space-y-2.5">
      {rows.map((a) => (
        <li key={a.agent} className="flex items-center gap-3 text-xs">
          <AgentAvatar agent={a.agent} size="sm" />
          <div className="min-w-0 flex-1">
            <div className="flex justify-between">
              <span>
                <span className="font-medium">{AGENTS[a.agent].name}</span>
                <span className="text-zinc-400"> · {a.calls} 次 · 平均 {formatMs(a.avg_duration_ms)}</span>
              </span>
              <span className="text-zinc-500">
                {formatTokens(a.tokens)} · {formatPct(a.tokens / total)}
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-zinc-100">
              <div
                className={`h-full rounded-full ${AGENTS[a.agent].color}`}
                style={{ width: `${(a.tokens / total) * 100}%` }}
              />
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}

export function RunTable({
  runs,
  showUser = false,
  onOpen,
}: {
  runs: RunSummary[]
  showUser?: boolean
  onOpen: (id: string) => void
}) {
  if (!runs.length) return <Empty text="还没有运行记录" />
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className={TH}>时间</th>
            {showUser && <th className={TH}>用户</th>}
            <th className={TH}>项目</th>
            <th className={TH}>类型</th>
            <th className={TH}>状态</th>
            <th className={TH}>检查</th>
            <th className={TH}>耗时</th>
            <th className={TH}>Token</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr
              key={r.id}
              onClick={() => onOpen(r.id)}
              className="cursor-pointer border-t border-zinc-100 hover:bg-violet-50/50"
            >
              <td className={`${TD} whitespace-nowrap text-zinc-500`}>{formatTime(r.created_at)}</td>
              {showUser && <td className={TD}>{r.username}</td>}
              <td className={`${TD} max-w-48 truncate`}>{r.project_title ?? '已删除'}</td>
              <td className={`${TD} whitespace-nowrap`}>
                {RUN_MODE_LABEL[r.mode]}
                {r.race_lanes > 1 && <span className="text-violet-600"> · Race×{r.race_lanes}</span>}
              </td>
              <td className={TD}>
                <RunStatusBadge status={r.status} />
              </td>
              <td className={TD}>
                {r.qa_ok === null ? (
                  <span className="text-zinc-300">-</span>
                ) : r.qa_ok ? (
                  <span className="text-emerald-600">通过</span>
                ) : (
                  <span className="text-amber-600">{r.qa_issues.length} 个问题</span>
                )}
              </td>
              <td className={TD}>{formatMs(r.duration_ms)}</td>
              <td className={TD}>{formatTokens(r.tokens)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Empty({ text = '暂无数据' }: { text?: string }) {
  return <p className="py-6 text-center text-xs text-zinc-400">{text}</p>
}
