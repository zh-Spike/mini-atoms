import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api, type Me } from './api'
import { AuthContext, useAuth } from './useAuth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(
    () =>
      api.me().then(
        (m) => setMe(m),
        () => setMe(null),
      ),
    [],
  )

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [refresh])

  return (
    <AuthContext.Provider value={{ me, loading, refresh, setMe }}>{children}</AuthContext.Provider>
  )
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth()
  const location = useLocation()
  if (loading) return <FullScreenSpinner />
  if (!me) return <Navigate to="/" replace state={{ from: location.pathname }} />
  return children
}

export function FullScreenSpinner() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="size-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
    </div>
  )
}
