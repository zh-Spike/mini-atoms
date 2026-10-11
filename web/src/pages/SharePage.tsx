import { SandpackPreview, SandpackProvider } from '@codesandbox/sandpack-react'
import { Sparkles } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError, type SharedApp } from '../lib/api'
import { FullScreenSpinner } from '../lib/auth'
import { toSandpack } from '../lib/sandpack'

/** Public, login-free page that runs a published app full screen. */
export default function SharePage() {
  const { slug = '' } = useParams()
  const [app, setApp] = useState<SharedApp | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getShared(slug, document.referrer).then(
      (a) => {
        setApp(a)
        document.title = `${a.title} · mini-atoms`
      },
      (err) => setError(err instanceof ApiError ? err.message : '加载失败'),
    )
  }, [slug])

  const sandpack = useMemo(() => (app ? toSandpack(app.files) : null), [app])

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-sm text-zinc-500">
        {error}
        <Link to="/" className="text-violet-600">
          去 mini-atoms 做一个自己的应用
        </Link>
      </div>
    )
  }
  if (!app || !sandpack) return <FullScreenSpinner />

  return (
    <div className="relative h-full">
      <SandpackProvider
        template="react"
        files={sandpack.files}
        customSetup={{ dependencies: sandpack.dependencies }}
        options={{ externalResources: sandpack.externalResources }}
        className="h-full"
      >
        <SandpackPreview
          className="h-full"
          showOpenInCodeSandbox={false}
          showRefreshButton={false}
          style={{ height: '100%' }}
        />
      </SandpackProvider>
      <Link
        to="/"
        className="absolute bottom-3 left-3 z-50 flex items-center gap-1 rounded-full bg-zinc-900/85 px-3 py-1.5 text-xs text-white shadow-lg backdrop-blur hover:bg-zinc-900"
      >
        <Sparkles className="size-3.5 text-violet-300" /> Made with mini-atoms
      </Link>
    </div>
  )
}
