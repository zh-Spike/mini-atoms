export function formatTime(iso: string): string {
  const hasZone = iso.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(iso)
  const d = new Date(hasZone ? iso : iso + 'Z')
  return d.toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** `2026-10-11` -> `10/11` */
export const shortDate = (iso: string) => iso.slice(5).replace('-', '/')

export function formatMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '-'
  if (ms < 1000) return `${ms} ms`
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} 秒`
  return `${Math.floor(ms / 60_000)} 分 ${Math.round((ms % 60_000) / 1000)} 秒`
}

export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`
  if (n >= 10_000) return `${(n / 1000).toFixed(1)}k`
  return n.toLocaleString()
}

export function formatPct(rate: number | null | undefined): string {
  return rate === null || rate === undefined ? '-' : `${(rate * 100).toFixed(rate === 1 ? 0 : 1)}%`
}

export function formatDuration(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d) return `${d} 天 ${h} 小时`
  if (h) return `${h} 小时 ${m} 分`
  return `${m} 分`
}

export const RUN_STATUS_LABEL = {
  running: '进行中',
  ok: '成功',
  error: '失败',
  aborted: '中断',
} as const

export const RUN_MODE_LABEL = {
  build: '新建',
  edit: '修改',
  rebuild: '重做',
} as const

export const SOURCE_LABEL = {
  ai: 'AI 生成',
  manual: '手动编辑',
  restore: '回滚',
  race: 'Race 候选',
} as const
