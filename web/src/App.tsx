import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { FullScreenSpinner, RequireAuth } from './lib/auth'
import Landing from './pages/Landing'
import Projects from './pages/Projects'

const Workbench = lazy(() => import('./pages/Workbench'))
const SharePage = lazy(() => import('./pages/SharePage'))
const Usage = lazy(() => import('./pages/Usage'))
const Admin = lazy(() => import('./pages/Admin'))
const Status = lazy(() => import('./pages/Status'))

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
      <Route
        path="/s/:slug"
        element={
          <Suspense fallback={<FullScreenSpinner />}>
            <SharePage />
          </Suspense>
        }
      />
      <Route
        path="/usage"
        element={
          <RequireAuth>
            <Suspense fallback={<FullScreenSpinner />}>
              <Usage />
            </Suspense>
          </RequireAuth>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <Suspense fallback={<FullScreenSpinner />}>
              <Admin />
            </Suspense>
          </RequireAuth>
        }
      />
      <Route
        path="/status"
        element={
          <Suspense fallback={<FullScreenSpinner />}>
            <Status />
          </Suspense>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
