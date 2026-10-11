import clsx from 'clsx'
import { Check, Copy, ExternalLink, Globe, Loader2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, ApiError, type ShareInfo, type ShareStats } from '../lib/api'
import { shortDate } from '../lib/format'
import { Bars } from './Stats'

interface Props {
  projectId: string
  share: ShareInfo | null
  latestVersionId: string | undefined
  latestNumber: number | undefined
  disabled: boolean
  onChange: (share: ShareInfo | null) => void
}

/** Publishes the latest version at a public `/s/{slug}` link. */
export default function ShareButton(props: Props) {
  const { projectId, share, latestVersionId, latestNumber, disabled, onChange } = props
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const url = share ? `${location.origin}/s/${share.slug}` : ''
  const outdated = share && latestVersionId && share.version_id !== latestVersionId

  async function act(fn: () => Promise<ShareInfo | null>) {
    setBusy(true)
    setError('')
    try {
      onChange(await fn())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '操作失败')
    } finally {
      setBusy(false)
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(url)
    } catch {
      window.prompt('复制链接', url)
      return
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        disabled={disabled}
        className={clsx(
          'flex items-center gap-1 rounded-md px-2.5 py-1 text-xs whitespace-nowrap disabled:opacity-40',
          share
            ? 'border border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
            : 'bg-zinc-900 text-white hover:bg-zinc-700',
        )}
      >
        <Globe className="size-3.5" /> {share ? '已发布' : '发布'}
      </button>
      {open && (
        <div className="absolute top-full right-0 z-20 mt-2 w-80 rounded-xl border border-zinc-200 bg-white p-4 text-sm shadow-xl">
          {share ? (
            <>
              <div className="font-medium">应用已公开发布</div>
              <p className="mt-1 text-xs text-zinc-500">
                任何人打开链接都能直接使用 v{share.version_number} · 已被访问 {share.views} 次
              </p>
              <div className="mt-3 flex items-center gap-1 rounded-lg border border-zinc-200 bg-zinc-50 p-1 pl-2">
                <span className="min-w-0 flex-1 truncate font-mono text-xs text-zinc-700">{url}</span>
                <button
                  onClick={() => void copy()}
                  className="rounded-md p-1.5 text-zinc-500 hover:bg-white hover:text-zinc-900"
                  aria-label="复制链接"
                >
                  {copied ? <Check className="size-3.5 text-emerald-600" /> : <Copy className="size-3.5" />}
                </button>
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-md p-1.5 text-zinc-500 hover:bg-white hover:text-zinc-900"
                  aria-label="打开"
                >
                  <ExternalLink className="size-3.5" />
                </a>
              </div>
              <ShareAnalytics projectId={projectId} slug={share.slug} />
              <div className="mt-3 flex items-center justify-between gap-2">
                <button
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      await api.unpublish(projectId)
                      return null
                    })
                  }
                  className="text-xs text-zinc-500 hover:text-red-600"
                >
                  取消发布
                </button>
                {outdated && (
                  <button
                    disabled={busy}
                    onClick={() => void act(() => api.publish(projectId))}
                    className="flex items-center gap-1 rounded-md bg-violet-600 px-2.5 py-1 text-xs text-white hover:bg-violet-700 disabled:opacity-50"
                  >
                    {busy && <Loader2 className="size-3 animate-spin" />}
                    更新到最新版本 v{latestNumber}
                  </button>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="font-medium">发布为公开应用</div>
              <p className="mt-1 text-xs text-zinc-500">
                把最新版本 v{latestNumber} 发布到一个公开链接，无需登录即可访问和使用。之后的修改需要手动更新发布。
              </p>
              <button
                disabled={busy || !latestVersionId}
                onClick={() => void act(() => api.publish(projectId))}
                className="mt-3 flex w-full items-center justify-center gap-1 rounded-lg bg-violet-600 py-2 text-sm text-white hover:bg-violet-700 disabled:opacity-50"
              >
                {busy && <Loader2 className="size-3.5 animate-spin" />} 发布
              </button>
            </>
          )}
          {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
        </div>
      )}
    </div>
  )
}

const DEVICE_LABEL = { desktop: '桌面', mobile: '手机' } as const

/** Last-7-day traffic of the published app, like a tiny analytics report. */
function ShareAnalytics({ projectId, slug }: { projectId: string; slug: string }) {
  const [stats, setStats] = useState<ShareStats | null>(null)

  useEffect(() => {
    let cancelled = false
    api.shareStats(projectId).then(
      (s) => !cancelled && setStats(s),
      () => {},
    )
    return () => {
      cancelled = true
    }
  }, [projectId, slug])

  if (!stats) return null
  const total = Math.max(1, stats.views_window)
  return (
    <div className="mt-3 rounded-lg border border-zinc-100 bg-zinc-50 p-3">
      <div className="mb-2 flex justify-between text-xs">
        <span className="text-zinc-500">近 7 天访问</span>
        <span className="font-medium">{stats.views_window} 次</span>
      </div>
      <Bars
        height={48}
        data={stats.daily.map((d) => ({
          label: shortDate(d.date),
          title: `${d.date}：${d.views} 次`,
          parts: [{ value: d.views, className: 'bg-emerald-400' }],
        }))}
      />
      {stats.views_window > 0 && (
        <div className="mt-2 grid grid-cols-2 gap-3 text-[11px] text-zinc-500">
          <div>
            <div className="mb-1 text-zinc-400">来源</div>
            {stats.referrers.map((r) => (
              <div key={r.host} className="flex justify-between gap-1">
                <span className="truncate">{r.host}</span>
                <span>{r.views}</span>
              </div>
            ))}
          </div>
          <div>
            <div className="mb-1 text-zinc-400">设备</div>
            {stats.devices.map((d) => (
              <div key={d.device} className="flex justify-between">
                <span>{DEVICE_LABEL[d.device]}</span>
                <span>{Math.round((d.views / total) * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
