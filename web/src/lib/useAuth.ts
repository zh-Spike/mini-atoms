import { createContext, useContext } from 'react'
import type { Me } from './api'

export interface AuthState {
  me: Me | null
  loading: boolean
  refresh: () => Promise<void>
  setMe: (me: Me | null) => void
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
