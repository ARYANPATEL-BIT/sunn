import { useEffect, useRef } from 'react'
import { createBrowserRouter, Navigate, Outlet, RouterProvider, ScrollRestoration, useLocation } from 'react-router-dom'
import AppShell from './AppShell.jsx'
import { AuthProvider, RequireAuth } from './auth.jsx'
import { LoginPage, SignupPage } from './AuthPages.jsx'
import Enroll from './Enroll.jsx'
import { LanguageProvider } from './i18n/index.jsx'
import Landing from './Landing.jsx'
import Onboarding from './Onboarding.jsx'
import Phrases from './Phrases.jsx'
import { applyPreferences } from './prefs.js'
import Progress from './Progress.jsx'
import Settings from './Settings.jsx'
import Speak from './Speak.jsx'
import { syncThemeColor } from './theme.js'

// The list screens sit on the tinted grouped background, like iOS Settings (DESIGN.md: themes).
const GROUPED = ['/app/phrases', '/app/progress', '/app/settings']

function Root() {
  const { pathname } = useLocation()
  const main = useRef(null)
  const first = useRef(true)

  // After a page change, move focus to the content for screen reader users.
  useEffect(() => {
    applyPreferences()
    document.documentElement.dataset.surface = GROUPED.includes(pathname) ? 'grouped' : 'plain'
    syncThemeColor()
    if (first.current) return void (first.current = false)
    main.current?.focus({ preventScroll: true })
  }, [pathname])

  return (
    <>
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
          { path: 'onboarding', element: <Onboarding /> },
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
