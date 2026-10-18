import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import * as api from './api.js'
import { useLang } from './i18n/index.jsx'
import { Alert } from './ui.jsx'

const AuthContext = createContext(null)

// The session itself is an httpOnly cookie; this only mirrors who it belongs to.
// status: 'loading' until GET /auth/me answers, then 'ready' (user or null) or 'error'.
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
    addEventListener(api.SIGNED_OUT, signedOut)
    return () => removeEventListener(api.SIGNED_OUT, signedOut)
  }, [refresh])

  const value = {
    ...state,
    refresh,
    signedIn: (user) => setState({ status: 'ready', user, error: null }),
    async logout() {
      await api.logout().catch(() => {}) // even if the server is down, forget the user here
      setState({ status: 'ready', user: null, error: null })
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

// /app/*: signed-out visitors go to /login, which brings them back here afterwards.
export function RequireAuth({ children }) {
  const { status, user, error, refresh } = useAuth()
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
        <button type="button" className="pill-outline" onClick={refresh}>
          {t('error.retry')}
        </button>
      </section>
    )
  }
  if (!user) return <Navigate replace to={loginPath(location.pathname + location.search)} />
  return children
}
