import clsx from 'clsx'
import { Code2, Eye, History, RotateCcw, Save, Sparkles } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import ChatPanel from '../components/ChatPanel'
import LiveCode from '../components/LiveCode'
import Logo from '../components/Logo'
import PipelineBar from '../components/PipelineBar'
import PreviewPanel from '../components/PreviewPanel'
import { useAgentRun } from '../hooks/useAgentRun'
import {
  api,
  ApiError,
  type AgentId,
  type Files,
  type Message,
  type ProjectDetail,
  type Version,
  type VersionMeta,
} from '../lib/api'
import { PIPELINE } from '../lib/agents'
import { useAuth } from '../lib/useAuth'
import { formatTime, SOURCE_LABEL } from '../lib/format'

export default function Workbench() {
  const { projectId = '' } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { me, refresh: refreshMe } = useAuth()

  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [loadError, setLoadError] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [versions, setVersions] = useState<VersionMeta[]>([])
  const [shown, setShown] = useState<Version | null>(null)
  const [tab, setTab] = useState<'preview' | 'code'>('preview')
  const [dirty, setDirty] = useState(false)
  const [saveRequest, setSaveRequest] = useState(0)
  const [notice, setNotice] = useState('')
  const hadVersionAtStart = useRef(false)
  const versionCache = useRef(new Map<string, Version>())

  const latestId = versions[0]?.id
  const versionNumbers = useMemo(
    () => Object.fromEntries(versions.map((v) => [v.id, v.number])),
    [versions],
  )

  const addVersion = useCallback((v: Version) => {
    versionCache.current.set(v.id, v)
    setVersions((vs) => [v, ...vs.filter((x) => x.id !== v.id)])
    setShown(v)
  }, [])

  const { run, start, stop } = useAgentRun(projectId, {
    onMessage: (m) => setMessages((ms) => [...ms.filter((x) => x.id !== m.id), m]),
    onVersion: (v, messageId) => {
      addVersion(v)
      setMessages((ms) => ms.map((m) => (m.id === messageId ? { ...m, version_id: v.id } : m)))
      setTab('preview')
    },
    onError: (text) =>
      setMessages((ms) => [
        ...ms,
        {
          id: `err-${Date.now()}`,
          role: 'system',
          agent: null,
          content: text,
          version_id: null,
          created_at: new Date().toISOString(),
        },
      ]),
    onFinish: () => void refreshMe(),
  })

  const send = useCallback(
    (text: string) => {
      hadVersionAtStart.current = versions.length > 0
      void start(text)
    },
    [start, versions.length],
  )

  const autoSent = useRef(false)
  useEffect(() => {
    let cancelled = false
    api.getProject(projectId).then(
      (p) => {
        if (cancelled) return
        setProject(p)
        setMessages(p.messages)
        setVersions(p.versions)
        if (p.latest_version) {
          versionCache.current.set(p.latest_version.id, p.latest_version)
          setShown(p.latest_version)
        }
        const auto = (location.state as { autoPrompt?: string } | null)?.autoPrompt
        if (auto && p.messages.length === 0 && !autoSent.current) {
          autoSent.current = true
          navigate(location.pathname, { replace: true, state: null })
          hadVersionAtStart.current = false
          void start(auto)
        }
      },
      (err) => setLoadError(err instanceof ApiError ? err.message : '加载失败'),
    )
    return () => {
      cancelled = true
    }
    // Load once per project; location state is consumed on first load only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  async function openVersion(id: string) {
    if (dirty && !confirm('当前有未保存的手动修改，切换版本会丢失，继续？')) return
    let v = versionCache.current.get(id)
    if (!v) {
      v = await api.getVersion(id)
      versionCache.current.set(id, v)
    }
    setShown(v)
  }

  async function restore() {
    if (!shown) return
    addVersion(await api.restoreVersion(shown.id))
    flash(`已回滚，生成了新版本`)
  }

  const saveFiles = useCallback(
    async (files: Files) => {
      addVersion(await api.saveVersion(projectId, files, '手动编辑代码'))
      setDirty(false)
      flash('已保存为新版本')
    },
    [projectId, addVersion],
  )

  function flash(text: string) {
    setNotice(text)
    setTimeout(() => setNotice(''), 2500)
  }

  const fixError = useCallback(
    (error: string) => send(`预览运行时报错了，请修复：\n${error.slice(0, 1500)}`),
    [send],
  )

  if (loadError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-sm text-zinc-500">
        {loadError}
        <button onClick={() => navigate('/projects')} className="text-violet-600">
          返回项目列表
        </button>
      </div>
    )
  }

  const running = run !== null
  const active: AgentId | null = run?.live?.agent ?? null
  const seen = run ? [...run.completed, ...(active ? [active] : [])] : []
  const steps: AgentId[] = !hadVersionAtStart.current
    ? PIPELINE
    : seen.includes('emma')
      ? ['mike', ...PIPELINE]
      : ['mike', 'alex', 'qa']
  const liveFileCount = run ? Object.keys(run.liveFiles).length : 0
  const showLiveCode = running && liveFileCount > 0 && (active === 'alex' || !shown)
  const doneFiles = new Set(
    run?.live?.files.filter((f) => f.done).map((f) => f.path) ?? Object.keys(run?.liveFiles ?? {}),
  )
  const viewingOld = shown && latestId && shown.id !== latestId

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-zinc-200 bg-white px-4">
        <div className="flex min-w-0 items-center gap-3">
          <Logo />
          <span className="text-zinc-300">/</span>
          <span className="truncate text-sm font-medium">{project?.title ?? '…'}</span>
        </div>
        <div className="text-xs text-zinc-500">
          剩余生成次数 {me ? me.generation_limit - me.generations_used : '-'}
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="w-[340px] shrink-0 border-r border-zinc-200 bg-zinc-50 xl:w-[400px]">
          <ChatPanel
            messages={messages}
            live={run?.live ?? null}
            running={running}
            versionNumbers={versionNumbers}
            onSend={send}
            onStop={stop}
            onOpenVersion={(id) => void openVersion(id)}
          />
        </aside>

        <section className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-11 shrink-0 items-center justify-between gap-3 border-b border-zinc-200 bg-white px-3">
            <div className="flex items-center gap-1 rounded-lg bg-zinc-100 p-0.5">
              <TabButton active={tab === 'preview'} onClick={() => setTab('preview')}>
                <Eye className="size-3.5" /> 预览
              </TabButton>
              <TabButton active={tab === 'code'} onClick={() => setTab('code')}>
                <Code2 className="size-3.5" /> 代码
              </TabButton>
            </div>

            {running ? (
              <PipelineBar steps={steps} active={active} completed={run.completed} />
            ) : notice ? (
              <span className="text-xs text-emerald-600">{notice}</span>
            ) : null}

            <div className="flex items-center gap-2">
              {dirty && !running && (
                <button
                  onClick={() => setSaveRequest((n) => n + 1)}
                  className="flex items-center gap-1 rounded-md bg-violet-600 px-2.5 py-1 text-xs whitespace-nowrap text-white hover:bg-violet-700"
                >
                  <Save className="size-3.5" /> 保存为新版本
                </button>
              )}
              {viewingOld && !running && (
                <button
                  onClick={() => void restore()}
                  className="flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs whitespace-nowrap text-amber-800 hover:bg-amber-100"
                >
                  <RotateCcw className="size-3.5" /> 回滚到此版本
                </button>
              )}
              {versions.length > 0 && (
                <label className="flex items-center gap-1 text-xs text-zinc-500">
                  <History className="size-3.5" />
                  <select
                    value={shown?.id ?? ''}
                    disabled={running}
                    onChange={(e) => void openVersion(e.target.value)}
                    className="rounded-md border border-zinc-200 bg-white px-1.5 py-1 text-xs text-zinc-800"
                  >
                    {versions.map((v) => (
                      <option key={v.id} value={v.id}>
                        v{v.number} · {SOURCE_LABEL[v.source]} · {formatTime(v.created_at)}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
          </div>

          <div className="relative min-h-0 flex-1 bg-white">
            {showLiveCode && run ? (
              <LiveCode files={run.liveFiles} currentFile={run.currentFile} doneFiles={doneFiles} />
            ) : shown ? (
              <PreviewPanel
                files={shown.files}
                versionKey={shown.id}
                tab={tab}
                canFix={!running && !viewingOld}
                onSave={(f) => void saveFiles(f)}
                onDirtyChange={setDirty}
                onFixError={fixError}
                saveRequest={saveRequest}
              />
            ) : (
              <EmptyState running={running} />
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center gap-1 rounded-md px-2.5 py-1 text-xs whitespace-nowrap',
        active ? 'bg-white font-medium text-zinc-900 shadow-sm' : 'text-zinc-500',
      )}
    >
      {children}
    </button>
  )
}

function EmptyState({ running }: { running: boolean }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <div
        className={clsx(
          'flex size-14 items-center justify-center rounded-2xl bg-violet-50',
          running && 'animate-pulse',
        )}
      >
        <Sparkles className="size-7 text-violet-500" />
      </div>
      <p className="text-sm text-zinc-500">
        {running ? '团队正在梳理需求和架构，马上开始写代码…' : '在左侧描述你的应用，预览会出现在这里'}
      </p>
    </div>
  )
}
