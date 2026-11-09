import { useEffect } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { usePresenterMode } from './prefs.js'
import PresenterBar from './PresenterBar.jsx'
import { Icon, LangToggle, reducedMotion, ThemeToggle, Wordmark } from './ui/index.js'
import { TabFace, TABS } from './ui/Tabs.jsx'

// Every /app screen: a header (home, presenter mode, language, theme; on wide screens who is
// signed in and log out, which phones find in Settings) and the tabs along the bottom.
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
    <div className="app">
      <header className="app-header">
        <div className="bar">
          <Wordmark />
          <div className="bar-end">
            <NavLink to="/trainings" className="nav-link wide-only" viewTransition={!reducedMotion()}>
              {t('nav.trainings')}
            </NavLink>
            <button
              type="button"
              className="icon-button presenter-toggle"
              onClick={togglePresenter}
              aria-pressed={presenterMode}
              title={presenterMode ? t('presenter.exit') : t('presenter.enter')}
              aria-label={presenterMode ? t('presenter.exit') : t('presenter.enter')}
            >
              <Icon name="presentation" />
              <span className="wide-only">{t('presenter.shortLabel')}</span>
            </button>
            <LangToggle />
            <ThemeToggle />
            <span className="who wide-only">
              <span className="visually-hidden">{t('app.signedIn', { name: user.name })}</span>
              <span aria-hidden="true">{user.name}</span>
            </span>
            <button type="button" className="button small wide-only" onClick={logout}>
              <Icon name="logOut" />
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
          {TABS.map(({ to, key, icon }) => (
            <NavLink key={to} to={to} className="tab" viewTransition={!reducedMotion()}>
              <TabFace k={key} icon={icon} />
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
