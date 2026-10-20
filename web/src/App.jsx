import { useEffect, useRef } from 'react'
import { createBrowserRouter, Navigate, Outlet, RouterProvider, ScrollRestoration, useLocation } from 'react-router-dom'
import AppShell from './AppShell.jsx'
import { AuthProvider, RequireAuth } from './auth.jsx'
import { LoginPage, SignupPage } from './AuthPages.jsx'
import Enroll from './Enroll.jsx'
import { LanguageProvider } from './i18n/index.jsx'
import Landing from './Landing.jsx'
import Phrases from './Phrases.jsx'
import { applyPreferences } from './prefs.js'
import Progress from './Progress.jsx'
import SeaLight from './SeaLight.jsx'
import Settings from './Settings.jsx'
import Speak from './Speak.jsx'

// Background per page (DESIGN.md): light intensity, and the sky veil over it.
// The veils keep text at WCAG AA over the brightest pixel the light can reach (README: contrast).
const SEA = { '/': [1, 0], '/login': [0.8, 0.25], '/signup': [0.8, 0.25], '/app/speak': [0.45, 0.35] }
const SEA_DEFAULT = [0.55, 0.45]

function Root() {
  const { pathname } = useLocation()
  const main = useRef(null)
  const first = useRef(true)
  const [intensity, veil] = SEA[pathname] || SEA_DEFAULT

  // After a page change, move focus to the content for screen reader users.
  useEffect(() => {
    applyPreferences()
    if (first.current) return void (first.current = false)
    main.current?.focus({ preventScroll: true })
  }, [pathname])

  return (
    <>
      <SeaLight intensity={intensity} veil={veil} />
      <div ref={main} tabIndex={-1} className="page">
        <Outlet />
      </div>
      <ScrollRestoration />
    </>
  )
}

const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      { path: '/', element: <Landing /> },
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
      {
        path: '/app',
        element: (
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        ),
        children: [
          { index: true, element: <Navigate replace to="/app/speak" /> },
          { path: 'enroll', element: <Enroll /> },
          { path: 'speak', element: <Speak /> },
          { path: 'phrases', element: <Phrases /> },
          { path: 'progress', element: <Progress /> },
          { path: 'settings', element: <Settings /> },
        ],
      },
      { path: '*', element: <Navigate replace to="/" /> },
    ],
  },
])

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </LanguageProvider>
  )
}
