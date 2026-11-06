import { AudioLines, BookOpen, ChartNoAxesColumn, LogOut, Mic, Presentation, Settings as SettingsIcon } from 'lucide-react'
import { useEffect } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { usePresenterMode } from './prefs.js'
import PresenterBar from './PresenterBar.jsx'
import { ICON, LangToggle, reducedMotion, ThemeToggle, Wordmark } from './ui.jsx'

const TABS = [
  { to: '/app/enroll', key: 'tab.enroll', Icon: AudioLines },
  { to: '/app/speak', key: 'tab.speak', Icon: Mic },
  { to: '/app/phrases', key: 'tab.phrases', Icon: BookOpen },
  { to: '/app/progress', key: 'tab.progress', Icon: ChartNoAxesColumn },
  { to: '/app/settings', key: 'tab.settings', Icon: SettingsIcon },
]

// Every /app screen: a header (home, presenter mode, language, theme; on wide screens who is
// signed in and log out, which phones find in Settings) and the bottom tabs.
export default function AppShell() {
  const { user, logout } = useAuth()
  const { t } = useLang()
  const [presenterMode, togglePresenter] = usePresenterMode()

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.altKey && (e.key === 'p' || e.key === 'P')) {
        e.preventDefault()
        togglePresenter()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [togglePresenter])

  return (
    <>
      <header className="app-header">
        <div className="bar">
          <Wordmark />
          <div className="bar-end">
            <button
              type="button"
              className="icon-button presenter-toggle"
              onClick={togglePresenter}
              aria-pressed={presenterMode}
              title={presenterMode ? t('presenter.exit') : t('presenter.enter')}
              aria-label={presenterMode ? t('presenter.exit') : t('presenter.enter')}
            >
              <Presentation {...ICON} />
              <span className="wide-only">{t('presenter.shortLabel')}</span>
            </button>
            <LangToggle />
            <ThemeToggle />
            <span className="who wide-only">
              <span className="visually-hidden">{t('app.signedIn', { name: user.name })}</span>
              <span aria-hidden="true">{user.name}</span>
            </span>
            <button type="button" className="button small wide-only" onClick={logout}>
              <LogOut {...ICON} />
              <span>{t('app.logOut')}</span>
            </button>
          </div>
        </div>
      </header>

      {presenterMode && <PresenterBar onClose={togglePresenter} />}

      <main className="app-main">
        <Outlet />
      </main>

      <nav className="tabs" aria-label={t('app.nav')}>
        <div className="tabs-inner">
          {TABS.map(({ to, key, Icon }) => (
            <NavLink key={to} to={to} className="tab" viewTransition={!reducedMotion()}>
              <Icon {...ICON} />
              <span>{t(key)}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </>
  )
}
