import { AudioLines, BookOpen, ChartNoAxesColumn, LogOut, Mic } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { LangToggle, reducedMotion, useGo, Wordmark } from './ui.jsx'

const TABS = [
  { to: '/app/enroll', key: 'tab.enroll', Icon: AudioLines },
  { to: '/app/speak', key: 'tab.speak', Icon: Mic },
  { to: '/app/phrases', key: 'tab.phrases', Icon: BookOpen },
  { to: '/app/progress', key: 'tab.progress', Icon: ChartNoAxesColumn },
]

// Every /app screen: a header (home, language, who is signed in, log out) and the bottom tabs.
export default function AppShell() {
  const { user, logout } = useAuth()
  const { t } = useLang()
  const go = useGo()

  async function logOut() {
    await logout()
    go('/', { replace: true })
  }

  return (
    <>
      <header className="app-header">
        <Wordmark />
        <div className="app-header-end">
          <LangToggle />
          <span className="who" title={t('app.signedIn', { name: user.name })}>
            <span className="visually-hidden">{t('app.signedIn', { name: user.name })}</span>
            <span aria-hidden="true">{user.name}</span>
          </span>
          <button type="button" className="pill-outline logout" onClick={logOut}>
            <LogOut aria-hidden="true" strokeWidth={1.5} />
            <span>{t('app.logOut')}</span>
          </button>
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <nav className="tabs" aria-label={t('app.nav')}>
        {TABS.map(({ to, key, Icon }) => (
          <NavLink key={to} to={to} viewTransition={!reducedMotion()}>
            <Icon aria-hidden="true" strokeWidth={1.5} />
            <span>{t(key)}</span>
          </NavLink>
        ))}
      </nav>
    </>
  )
}
