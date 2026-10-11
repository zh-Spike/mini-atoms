import clsx from 'clsx'
import {
  Code2,
  Download,
  Eye,
  History,
  MessageSquare,
  Monitor,
  RotateCcw,
  Save,
  Smartphone,
  Sparkles,
  Swords,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import ChatPanel from '../components/ChatPanel'
import LiveCode from '../components/LiveCode'
import Logo from '../components/Logo'
import PipelineBar from '../components/PipelineBar'
import PreviewPanel, { type Device } from '../components/PreviewPanel'
import QuotaBadge from '../components/QuotaBadge'
import { RaceLive, RacePicker, type RaceCandidate } from '../components/RaceBoard'
import RunTraceDrawer from '../components/RunTrace'
import ShareButton from '../components/ShareButton'
import { useAgentRun } from '../hooks/useAgentRun'
import {
  api,
  ApiError,
  type AgentId,
  type Files,
  type Message,
  type ProjectDetail,
  type RunStats,
  type ShareInfo,
  type Version,
  type VersionMeta,
} from '../lib/api'
import { laneName, PIPELINE } from '../lib/agents'
import { downloadProjectZip } from '../lib/exportZip'
import { useAuth } from '../lib/useAuth'
import { formatTime, SOURCE_LABEL } from '../lib/format'

const noop = () => {}

function versionLabel(v: VersionMeta): string {
  if (!v.label) return SOURCE_LABEL[v.source]
  return v.source === 'race' ? v.label : `采用 ${v.label}`
}

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
  const [device, setDevice] = useState<Device>('desktop')
  const [pane, setPane] = useState<'chat' | 'preview'>('chat')
  const [dirty, setDirty] = useState(false)
  const [saveRequest, setSaveRequest] = useState(0)
  const [notice, setNotice] = useState('')
  const [share, setShare] = useState<ShareInfo | null>(null)
  const [stats, setStats] = useState<RunStats | null>(null)
  const [lastRunId, setLastRunId] = useState<string | null>(null)
  const [traceId, setTraceId] = useState<string | null>(null)
  const [candidates, setCandidates] = useState<RaceCandidate[] | null>(null)
  const [pick, setPick] = useState(0)
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

  const flash = useCallback((text: string, ms = 2500) => {
    setNotice(text)
    setTimeout(() => setNotice(''), ms)
  }, [])

  const { run, start, stop } = useAgentRun(projectId, {
    onMessage: (m) => setMessages((ms) => [...ms.filter((x) => x.id !== m.id), m]),
    onVersion: (v, messageId) => {
      addVersion(v)
      setMessages((ms) => ms.map((m) => (m.id === messageId ? { ...m, version_id: v.id } : m)))
      setTab('preview')
      setPane('preview')
    },
    onLaneDone: (lane, label, v, m) => {
      addVersion(v)
      setMessages((ms) => [...ms, m])
      setCandidates((cs) => [...(cs ?? []), { lane, label, version: v }])
      setPane('preview')
    },
    onNotice: (text) => flash(text, 5000),
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
    onFinish: (s, runId) => {
      setStats(s)
      setLastRunId(runId)
      void refreshMe()
    },
  })

  const send = useCallback(
    (text: string, raceModels: string[] | null = null) => {
      hadVersionAtStart.current = versions.length > 0
      setCandidates(null)
      setPick(0)
      void start(text, raceModels)
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
        setShare(p.share)
        if (p.latest_version) {
          versionCache.current.set(p.latest_version.id, p.latest_version)
          setShown(p.latest_version)
          setPane('preview')
        }
        const state = location.state as {
          autoPrompt?: string
          raceModels?: string[] | null
        } | null
        if (state?.autoPrompt && p.messages.length === 0 && !autoSent.current) {
          autoSent.current = true
          navigate(location.pathname, { replace: true, state: null })
          hadVersionAtStart.current = false
          void start(state.autoPrompt, state.raceModels ?? null)
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
    setPane('preview')
  }

  async function restore() {
    if (!shown) return
    addVersion(await api.restoreVersion(shown.id))
    flash(`已回滚，生成了新版本`)
  }

  async function adopt() {
    if (!candidates) return
    const c = candidates[pick]
    addVersion(await api.restoreVersion(c.version.id))
    setCandidates(null)
    flash(`已采用${laneName(c.lane)}，生成了新版本`)
  }

  const saveFiles = useCallback(
    async (files: Files) => {
      addVersion(await api.saveVersion(projectId, files, '手动编辑代码'))
      setDirty(false)
      flash('已保存为新版本')
    },
    [projectId, addVersion, flash],
  )

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
  const racing = Boolean(run?.race)
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
  const picking = !running && candidates !== null && candidates.length > 0
  const display = picking ? candidates[pick].version : shown
  const viewingOld = !picking && shown && latestId && shown.id !== latestId

  let main: React.ReactNode
  if (run?.race) main = <RaceLive lanes={run.race} />
  else if (showLiveCode && run)
    main = <LiveCode files={run.liveFiles} currentFile={run.currentFile} doneFiles={doneFiles} />
  else if (display)
    main = (
      <PreviewPanel
        files={display.files}
        versionKey={display.id}
        tab={tab}
        device={device}
        canFix={!running && !viewingOld && !picking}
        onSave={picking ? noop : (f) => void saveFiles(f)}
        onDirtyChange={setDirty}
        onFixError={fixError}
        saveRequest={saveRequest}
      />
    )
  else main = <EmptyState running={running} />

  return (
    <div className="flex h-full flex-col">
      <header className="flex h-12 shrink-0 items-center justify-between gap-2 border-b border-zinc-200 bg-white px-4">
        <div className="flex min-w-0 items-center gap-3">
          <Logo compact />
          <span className="text-zinc-300">/</span>
          <span className="truncate text-sm font-medium">{project?.title ?? '…'}</span>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <div className="flex items-center gap-0.5 rounded-lg bg-zinc-100 p-0.5 md:hidden">
            <TabButton active={pane === 'chat'} onClick={() => setPane('chat')}>
              <MessageSquare className="size-3.5" /> 对话
            </TabButton>
            <TabButton active={pane === 'preview'} onClick={() => setPane('preview')}>
              <Eye className="size-3.5" /> 应用
            </TabButton>
          </div>
          <QuotaBadge me={me} className="hidden sm:flex" />
          <ShareButton
            projectId={projectId}
            share={share}
            latestVersionId={latestId}
            latestNumber={versions[0]?.number}
            disabled={!latestId}
            onChange={(s) => {
              setShare(s)
              flash(s ? '已发布，链接可公开访问' : '已取消发布')
            }}
          />
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside
          className={clsx(
            'w-full shrink-0 border-r border-zinc-200 bg-zinc-50 md:block md:w-[340px] xl:w-[400px]',
            pane === 'chat' ? 'block' : 'hidden',
          )}
        >
          <ChatPanel
            messages={messages}
            live={run?.live ?? null}
            running={running}
            versionNumbers={versionNumbers}
            stats={stats}
            onShowTrace={lastRunId ? () => setTraceId(lastRunId) : undefined}
            onSend={(text, raceModels) => {
              send(text, raceModels)
              if (raceModels) setPane('preview')
            }}
            onStop={stop}
            onOpenVersion={(id) => void openVersion(id)}
          />
        </aside>

        <section
          className={clsx(
            'min-w-0 flex-1 flex-col md:flex',
            pane === 'preview' ? 'flex' : 'hidden',
          )}
        >
          <div className="flex h-11 shrink-0 items-center justify-between gap-3 overflow-x-auto border-b border-zinc-200 bg-white px-3">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 rounded-lg bg-zinc-100 p-0.5">
                <TabButton active={tab === 'preview'} onClick={() => setTab('preview')}>
                  <Eye className="size-3.5" /> 预览
                </TabButton>
                <TabButton active={tab === 'code'} onClick={() => setTab('code')}>
                  <Code2 className="size-3.5" /> 代码
                </TabButton>
              </div>
              {tab === 'preview' && (
                <div className="hidden items-center gap-0.5 rounded-lg bg-zinc-100 p-0.5 sm:flex">
                  <IconToggle
                    active={device === 'desktop'}
                    onClick={() => setDevice('desktop')}
                    label="桌面尺寸"
                  >
                    <Monitor className="size-3.5" />
                  </IconToggle>
                  <IconToggle
                    active={device === 'mobile'}
                    onClick={() => setDevice('mobile')}
                    label="手机尺寸"
                  >
                    <Smartphone className="size-3.5" />
                  </IconToggle>
                </div>
              )}
            </div>

            {racing ? (
              <span className="flex items-center gap-1 text-xs whitespace-nowrap text-violet-700">
                <Swords className="size-3.5" /> Race：{run?.race?.length} 个模型并行编写中
              </span>
            ) : running ? (
              <PipelineBar steps={steps} active={active} completed={run.completed} />
            ) : notice ? (
              <span className="text-xs whitespace-nowrap text-emerald-600">{notice}</span>
            ) : null}

            <div className="flex items-center gap-2">
              {dirty && !running && !picking && (
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
              {display && !running && (
                <button
                  onClick={() => downloadProjectZip(project?.title ?? 'app', display.files)}
                  title="导出为可本地运行的 React 项目（npm install && npm start）"
                  className="flex items-center gap-1 rounded-md px-2 py-1 text-xs whitespace-nowrap text-zinc-600 hover:bg-zinc-100"
                >
                  <Download className="size-3.5" /> 导出
                </button>
              )}
              {versions.length > 0 && (
                <label className="flex items-center gap-1 text-xs text-zinc-500">
                  <History className="size-3.5" />
                  <select
                    value={display?.id ?? ''}
                    disabled={running}
                    onChange={(e) => {
                      setCandidates(null)
                      void openVersion(e.target.value)
                    }}
                    className="max-w-48 rounded-md border border-zinc-200 bg-white px-1.5 py-1 text-xs text-zinc-800"
                  >
                    {versions.map((v) => (
                      <option key={v.id} value={v.id}>
                        v{v.number} · {versionLabel(v)} · {formatTime(v.created_at)}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </div>
          </div>

          {picking && (
            <RacePicker
              candidates={candidates}
              selected={pick}
              onSelect={setPick}
              onAdopt={() => void adopt()}
              onDismiss={() => setCandidates(null)}
            />
          )}

          <div className="relative min-h-0 flex-1 bg-white">{main}</div>
        </section>
      </div>
      {traceId && <RunTraceDrawer runId={traceId} onClose={() => setTraceId(null)} />}
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

function IconToggle({
  active,
  onClick,
  label,
  children,
}: {
  active: boolean
  onClick: () => void
  label: string
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      aria-label={label}
      className={clsx(
        'rounded-md p-1.5',
        active ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-400 hover:text-zinc-700',
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
