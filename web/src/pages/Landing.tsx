import { ArrowRight, KeyRound } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import AgentAvatar from '../components/AgentAvatar'
import Logo from '../components/Logo'
import { api, ApiError } from '../lib/api'
import { AGENTS, PIPELINE } from '../lib/agents'
import { FullScreenSpinner } from '../lib/auth'
import { useAuth } from '../lib/useAuth'

const INPUT =
  'w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100'

export default function Landing() {
  const { me, loading, setMe } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const from = (location.state as { from?: string } | null)?.from ?? '/projects'

  if (loading) return <FullScreenSpinner />
  if (me) return <Navigate to={from} replace />

  const isRegister = mode === 'register'
  const canSubmit = username.trim() && password && (!isRegister || code.trim())

  function switchMode(next: 'login' | 'register') {
    setMode(next)
    setError('')
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    const name = username.trim()
    if (isRegister) {
      if (!/^[A-Za-z0-9_]{3,32}$/.test(name)) {
        setError('用户名需为 3-32 位字母、数字或下划线')
        return
      }
      if (password.length < 6) {
        setError('密码至少 6 位')
        return
      }
    }
    setSubmitting(true)
    setError('')
    try {
      setMe(
        isRegister
          ? await api.register(code.trim(), name, password)
          : await api.login(name, password),
      )
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : '网络错误，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="relative min-h-full overflow-hidden">
      <div className="pointer-events-none absolute inset-x-0 -top-40 h-[480px] bg-gradient-to-b from-violet-200/60 via-fuchsia-100/40 to-transparent blur-3xl" />
      <header className="relative mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Logo to="/" />
        <a
          href="https://github.com/zh-Spike/mini-atoms"
          target="_blank"
          rel="noreferrer"
          className="text-sm text-zinc-500 hover:text-zinc-900"
        >
          GitHub
        </a>
      </header>

      <main className="relative mx-auto flex max-w-3xl flex-col items-center px-6 pt-16 pb-24 text-center">
        <span className="rounded-full border border-violet-200 bg-white/70 px-3 py-1 text-xs text-violet-700">
          AI 智能体团队 · 一句话生成可运行的应用
        </span>
        <h1 className="mt-6 text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
          把想法交给你的
          <span className="bg-gradient-to-r from-violet-600 to-fuchsia-500 bg-clip-text text-transparent">
            {' '}
            AI 软件团队
          </span>
        </h1>
        <p className="mt-4 max-w-xl text-zinc-600">
          描述你想要的应用，产品经理写 PRD、架构师做设计、工程师写代码、测试把关质量，
          几十秒后就能在浏览器里直接使用，并继续用对话迭代。
        </p>

        <div className="mt-8 flex items-center gap-3">
          {PIPELINE.map((id, i) => (
            <div key={id} className="flex items-center gap-3">
              <div className="flex items-center gap-2 rounded-full border border-zinc-200 bg-white py-1 pr-3 pl-1 shadow-sm">
                <AgentAvatar agent={id} size="sm" />
                <span className="text-xs text-zinc-600">{AGENTS[id].role}</span>
              </div>
              {i < PIPELINE.length - 1 && <ArrowRight className="size-3.5 text-zinc-300" />}
            </div>
          ))}
        </div>

        <form
          onSubmit={submit}
          className="mt-12 w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 text-left shadow-lg shadow-violet-100"
        >
          <div className="flex rounded-lg bg-zinc-100 p-1 text-sm">
            {(['login', 'register'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => switchMode(m)}
                className={`flex-1 rounded-md py-1.5 font-medium ${
                  mode === m ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500'
                }`}
              >
                {m === 'login' ? '登录' : '注册'}
              </button>
            ))}
          </div>
          <div className="mt-4 space-y-3">
            <input
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="用户名"
              autoComplete="username"
              className={INPUT}
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isRegister ? '密码（至少 6 位）' : '密码'}
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              className={INPUT}
            />
            {isRegister && (
              <div className="relative">
                <KeyRound className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-violet-600" />
                <input
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="邀请码"
                  className={`${INPUT} pl-9`}
                />
              </div>
            )}
            <button
              disabled={submitting || !canSubmit}
              className="w-full rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
            >
              {submitting ? '请稍候…' : isRegister ? '注册并进入' : '登录'}
            </button>
          </div>
          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
          <p className="mt-3 text-xs text-zinc-400">
            {isRegister
              ? '注册需要邀请码，用于控制模型调用成本。注册后用账号登录即可，在任何设备上都能访问你的项目。'
              : '还没有账号？切换到「注册」，用邀请码创建账号。'}
          </p>
        </form>
      </main>
      <footer className="pb-6 text-center text-xs text-zinc-400">
        <Link to="/status" className="hover:text-zinc-600">
          服务状态
        </Link>
      </footer>
    </div>
  )
}
