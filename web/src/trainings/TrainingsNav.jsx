import { Link, NavLink, useLocation } from 'react-router-dom'
import { loginPath, useAuth } from '../auth.jsx'
import { useLang } from '../i18n/index.jsx'
import { Icon, LanguagePicker, reducedMotion, ThemeToggle, Wordmark } from '../ui/index.js'
import { LessonsLangNote } from './HonestNote.jsx'
import { TabFace, TABS } from '../ui/Tabs.jsx'

export function TrainingsNav({ backTo, backLabel }) {
  const { user, logout } = useAuth()
  const { t } = useLang()
  const location = useLocation()

  return (
    <>
      <header className="site-nav trainings-nav">
        <nav className="bar" aria-label={t('nav.main')}>
          <div className="trainings-nav-start">
            <Wordmark />
            {backTo && (
              <Link
                to={backTo}
                className="trainings-back-link"
                aria-label={backLabel || t('trainings.backToTrainings')}
                viewTransition={!reducedMotion()}
              >
                <Icon name="arrowLeft" />
                <span className="back-link-text">{backLabel || t('trainings.backToTrainings')}</span>
              </Link>
            )}
          </div>
          <div className="bar-end">
            <LanguagePicker />
            <ThemeToggle />
            {user ? (
              <>
                <span className="who wide-only">
                  <span className="visually-hidden">{t('app.signedIn', { name: user.name })}</span>
                  <span aria-hidden="true">{user.name}</span>
                </span>
                <button type="button" className="button small wide-only" onClick={logout}>
                  <Icon name="logOut" />
                  <span>{t('app.logOut')}</span>
                </button>
              </>
            ) : (
              <Link
                to={loginPath(location.pathname + location.search)}
                className="nav-link"
                viewTransition={!reducedMotion()}
              >
                {t('nav.signIn')}
              </Link>
            )}
          </div>
        </nav>
      </header>
      <LessonsLangNote />

      {user && (
        <nav className="tabs" aria-label={t('app.nav')}>
          <div className="tabs-inner">
            {TABS.map(({ to, key, icon }) => (
              <NavLink key={to} to={to} className="tab" viewTransition={!reducedMotion()}>
                <TabFace k={key} icon={icon} />
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </>
  )
}
