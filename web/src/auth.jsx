import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import * as api from './api.js'
import { useLang } from './i18n/index.jsx'
import { forgetUser, isOnboarded } from './prefs.js'
import { Alert } from './ui/index.js'

const AuthContext = createContext(null)

// The session itself is an httpOnly cookie; this only mirrors who it belongs to.
// status: 'loading' until GET /auth/me answers, then 'ready' (user or null) or 'error'.
// left: the user signed out or deleted the account on purpose, so /app/* goes home, not to login.
export function AuthProvider({ children }) {
  const [state, setState] = useState({ status: 'loading', user: null, error: null })

  const refresh = useCallback(() => {
    setState((s) => ({ ...s, status: 'loading', error: null }))
    api.me().then(
      (user) => setState({ status: 'ready', user, error: null }),
      (error) => setState({ status: 'error', user: null, error }),
    )
  }, [])

  useEffect(() => {
    refresh()
    const signedOut = () => setState({ status: 'ready', user: null, error: null })
    const handleStorage = (e) => {
      if (e.key === 'sunn.auth_change') {
        refresh()
      }
    }
    addEventListener(api.SIGNED_OUT, signedOut)
    window.addEventListener('storage', handleStorage)
    return () => {
      removeEventListener(api.SIGNED_OUT, signedOut)
      window.removeEventListener('storage', handleStorage)
    }
  }, [refresh])

  useEffect(() => {
    if (state.left) {
      const timer = setTimeout(() => {
        setState((s) => (s.left ? { ...s, left: false } : s))
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [state.left])

  const notifyAuthChange = () => {
    try {
      localStorage.setItem('sunn.auth_change', String(Date.now()))
    } catch {
      // storage blocked
    }
  }

  const left = () => {
    api.stopAudio()
    setState({ status: 'ready', user: null, error: null, left: true })
    notifyAuthChange()
  }
  const value = {
    ...state,
    refresh,
    signedIn: (user) => {
      setState({ status: 'ready', user, error: null, left: false })
      notifyAuthChange()
    },
    async updateUser(changes) {
      const updated = await api.updateMe(changes)
      setState((s) => ({ ...s, user: updated }))
      notifyAuthChange()
      return updated
    },
    async logout() {
      await api.logout().catch(() => {}) // even if the server is down, forget the user here
      left()
    },
    // Deletes the account on the server (which also ends the session), then everything this
    // browser kept about it. Display preferences belong to the device and stay.
    async deleteAccount() {
      const userId = state.user?.id
      await api.deleteAccount()
      forgetUser(userId)
      left()
    },
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

// Only paths inside this site: "/x" yes; "//evil.com" and "/\evil.com" (both leave the site) no.
export function safeNext(next) {
  return typeof next === 'string' && /^\/(?![/\\])/.test(next) ? next : null
}

export const loginPath = (next) => `/login?next=${encodeURIComponent(next)}`

// Public routes: signed-in users are redirected to the application
export function RedirectIfAuthenticated({ children }) {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return null
  }
  if (user) {
    const searchParams = new URLSearchParams(location.search)
    const next = safeNext(searchParams.get('next'))
    const defaultRoute = isOnboarded(user.id) ? '/app/speak' : '/app/onboarding'
    return <Navigate replace to={next || defaultRoute} />
  }
  return children
}

// /app/*: signed-out visitors go to /login, which brings them back here afterwards.
export function RequireAuth({ children }) {
  const { status, user, error, refresh, left } = useAuth()
  const { t } = useLang()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <p className="screen-status" role="status">
        {t('app.loading')}
      </p>
    )
  }
  if (status === 'error') {
    return (
      <section className="screen narrow">
        <Alert error={error} />
        <button type="button" className="button" onClick={refresh}>
          {t('error.retry')}
        </button>
      </section>
    )
  }
  if (!user) return <Navigate replace to={left ? '/' : loginPath(location.pathname + location.search)} />
  return children
}
