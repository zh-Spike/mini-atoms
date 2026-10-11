import { ArrowUp, BarChart3, LogOut, Trash2 } from 'lucide-react'
import { useEffect, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import DemoBadge from '../components/DemoBadge'
import Logo from '../components/Logo'
import QuotaBadge from '../components/QuotaBadge'
import { RaceModelPicker, RaceToggle } from '../components/RaceControl'
import { api, ApiError, type ProjectSummary } from '../lib/api'
import { useModels } from '../lib/models'
import { useAuth } from '../lib/useAuth'
import { formatTime } from '../lib/format'

const EXAMPLES = [
  { title: '记账本', prompt: '做一个记账本，可以记录收支、按分类统计并用图表展示每月花销' },
  { title: '番茄钟', prompt: '做一个番茄钟，支持自定义专注和休息时长，记录今天完成了几个番茄' },
  { title: '习惯打卡', prompt: '做一个习惯打卡应用，可以添加习惯，每天打卡，并用热力图展示连续打卡记录' },
  { title: '看板', prompt: '做一个看板任务管理工具，有待办、进行中、已完成三列，任务可以在列之间移动' },
  { title: '单词卡', prompt: '做一个英语单词记忆卡片，支持翻面、标记已掌握，并按掌握程度复习' },
  { title: '2048', prompt: '做一个 2048 小游戏，支持键盘方向键操作，记录最高分' },
]

export default function Projects() {
  const { me, setMe } = useAuth()
  const navigate = useNavigate()
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null)
  const [prompt, setPrompt] = useState('')
  const [creating, setCreating] = useState(false)
  const [race, setRace] = useState<string[] | null>(null)
  const models = useModels()
  const [error, setError] = useState('')

  useEffect(() => {
    api.listProjects().then(setProjects, () => setProjects([]))
  }, [])

  async function create(text: string) {
    if (!text.trim() || creating) return
    setCreating(true)
    setError('')
    try {
      const project = await api.createProject(text.trim())
      navigate(`/p/${project.id}`, { state: { autoPrompt: text.trim(), raceModels: race } })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '创建失败')
      setCreating(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void create(prompt)
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      void create(prompt)
    }
  }

  async function remove(id: string) {
    if (!confirm('确定删除这个项目？')) return
    await api.deleteProject(id)
    setProjects((ps) => ps?.filter((p) => p.id !== id) ?? null)
  }

  async function logout() {
    await api.logout()
    setMe(null)
    navigate('/')
  }

  const quotaLeft = me ? me.generation_limit - me.generations_used : 0

  return (
    <div className="min-h-full">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Logo />
        <div className="flex items-center gap-4 text-sm text-zinc-500">
          {me && <span className="text-zinc-900">{me.username}</span>}
          <DemoBadge />
          <QuotaBadge me={me} />
          {me?.is_admin && (
            <Link to="/admin" className="flex items-center gap-1 hover:text-zinc-900">
              <BarChart3 className="size-4" /> 运营
            </Link>
          )}
          <button onClick={logout} className="flex items-center gap-1 hover:text-zinc-900">
            <LogOut className="size-4" /> 退出
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 pt-10 pb-20">
        <h1 className="text-center text-3xl font-semibold tracking-tight">今天想做个什么应用？</h1>
        <form
          onSubmit={onSubmit}
          className="mt-8 rounded-2xl border border-zinc-200 bg-white p-3 shadow-lg shadow-violet-100 focus-within:border-violet-400"
        >
          <textarea
            autoFocus
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="用一句话描述你的应用，例如：做一个带分类统计的记账本"
            className="w-full resize-none px-2 py-1 text-[15px] outline-none"
          />
          {race && models && <RaceModelPicker info={models} value={race} onChange={setRace} />}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RaceToggle info={models} value={race} onChange={setRace} disabled={quotaLeft < 2} />
              <span className="hidden text-xs text-zinc-400 sm:inline">
                {race
                  ? `${race.length} 个模型并行写，生成后对比择优`
                  : 'Enter 发送 · Shift+Enter 换行'}
              </span>
            </div>
            <button
              disabled={!prompt.trim() || creating}
              className="flex size-9 items-center justify-center rounded-full bg-violet-600 text-white hover:bg-violet-700 disabled:opacity-40"
              aria-label="开始生成"
            >
              <ArrowUp className="size-5" />
            </button>
          </div>
        </form>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.title}
              onClick={() => void create(ex.prompt)}
              disabled={creating}
              title={ex.prompt}
              className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-600 hover:border-violet-300 hover:text-violet-700"
            >
              {ex.title}
            </button>
          ))}
        </div>

        <section className="mt-16">
          <h2 className="text-sm font-medium text-zinc-500">我的项目</h2>
          {projects === null ? (
            <p className="mt-4 text-sm text-zinc-400">加载中…</p>
          ) : projects.length === 0 ? (
            <p className="mt-4 rounded-xl border border-dashed border-zinc-300 p-8 text-center text-sm text-zinc-400">
              还没有项目，从上面输入一个想法开始吧
            </p>
          ) : (
            <ul className="mt-4 grid gap-3 sm:grid-cols-2">
              {projects.map((p) => (
                <li key={p.id} className="group relative">
                  <Link
                    to={`/p/${p.id}`}
                    className="block rounded-xl border border-zinc-200 bg-white p-4 hover:border-violet-300 hover:shadow-sm"
                  >
                    <div className="truncate pr-8 font-medium">{p.title}</div>
                    <div className="mt-1 text-xs text-zinc-400">
                      {p.version_count} 个版本 · 更新于 {formatTime(p.updated_at)}
                    </div>
                  </Link>
                  <button
                    onClick={() => void remove(p.id)}
                    className="absolute top-4 right-4 hidden text-zinc-400 group-hover:block hover:text-red-600"
                    aria-label="删除项目"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
