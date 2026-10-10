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

export const SOURCE_LABEL = {
  ai: 'AI 生成',
  manual: '手动编辑',
  restore: '回滚',
  race: 'Race 候选',
} as const
