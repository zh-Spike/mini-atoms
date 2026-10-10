import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { FullScreenSpinner, RequireAuth } from './lib/auth'
import Landing from './pages/Landing'
import Projects from './pages/Projects'

const Workbench = lazy(() => import('./pages/Workbench'))

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/projects"
        element={
          <RequireAuth>
            <Projects />
          </RequireAuth>
        }
      />
      <Route
        path="/p/:projectId"
        element={
          <RequireAuth>
            <Suspense fallback={<FullScreenSpinner />}>
              <Workbench />
            </Suspense>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
