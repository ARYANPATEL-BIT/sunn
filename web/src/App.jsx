import { lazy, Suspense, useEffect, useRef } from 'react'
import { createBrowserRouter, Navigate, Outlet, RouterProvider, ScrollRestoration, useLocation } from 'react-router-dom'
import AppShell from './AppShell.jsx'
import { AuthProvider, RedirectIfAuthenticated, RequireAuth } from './auth.jsx'
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

const TrainingsHome = lazy(() => import('./trainings/TrainingsHome.jsx').then((m) => ({ default: m.TrainingsHome })))
const EasierWays = lazy(() => import('./trainings/EasierWays.jsx').then((m) => ({ default: m.EasierWays })))
const CategoryPage = lazy(() => import('./trainings/CategoryPage.jsx').then((m) => ({ default: m.CategoryPage })))
const CoursePage = lazy(() => import('./trainings/CoursePage.jsx').then((m) => ({ default: m.CoursePage })))
const LessonPlayer = lazy(() => import('./trainings/LessonPlayer.jsx').then((m) => ({ default: m.LessonPlayer })))

function Root() {
  const { pathname } = useLocation()
  const main = useRef(null)
  const first = useRef(true)

  // After a page change, move focus to the content for screen reader users.
  useEffect(() => {
    applyPreferences()
    syncThemeColor()
    if (first.current) return void (first.current = false)
    main.current?.focus({ preventScroll: true })
  }, [pathname])

  return (
    <>
      <div ref={main} tabIndex={-1} className="page">
        <Suspense fallback={null}>
          <Outlet />
        </Suspense>
      </div>
      <ScrollRestoration />
    </>
  )
}

const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      {
        path: '/',
        element: (
          <RedirectIfAuthenticated>
            <Landing />
          </RedirectIfAuthenticated>
        ),
      },
      {
        path: '/privacy',
        element: (
          <RedirectIfAuthenticated>
            <Landing initialSection="privacy" />
          </RedirectIfAuthenticated>
        ),
      },
      {
        path: '/faq',
        element: (
          <RedirectIfAuthenticated>
            <Landing initialSection="faq" />
          </RedirectIfAuthenticated>
        ),
      },
      {
        path: '/questions',
        element: (
          <RedirectIfAuthenticated>
            <Landing initialSection="faq" />
          </RedirectIfAuthenticated>
        ),
      },
      {
        path: '/how',
        element: (
          <RedirectIfAuthenticated>
            <Landing initialSection="how" />
          </RedirectIfAuthenticated>
        ),
      },
      {
        path: '/how-it-works',
        element: (
          <RedirectIfAuthenticated>
            <Landing initialSection="how" />
          </RedirectIfAuthenticated>
        ),
      },
      {
        path: '/login',
        element: (
          <RedirectIfAuthenticated>
            <LoginPage />
          </RedirectIfAuthenticated>
        ),
      },
      {
        path: '/signup',
        element: (
          <RedirectIfAuthenticated>
            <SignupPage />
          </RedirectIfAuthenticated>
        ),
      },
      { path: '/trainings', element: <TrainingsHome /> },
      { path: '/trainings/easier-ways', element: <EasierWays /> },
      { path: '/trainings/:categoryId', element: <CategoryPage /> },
      { path: '/trainings/:categoryId/:courseId', element: <CoursePage /> },
      { path: '/trainings/:categoryId/:courseId/:lessonId', element: <LessonPlayer /> },
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
          { path: 'trainings', element: <Navigate replace to="/trainings" /> },
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
