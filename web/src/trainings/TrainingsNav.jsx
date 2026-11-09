import { Link, NavLink, useLocation } from 'react-router-dom'
import { loginPath, useAuth } from '../auth.jsx'
import { useLang } from '../i18n/index.jsx'
import { Icon, LangToggle, reducedMotion, ThemeToggle, Wordmark } from '../ui/index.js'
import { TabFace, TABS } from '../ui/Tabs.jsx'

export function TrainingsNav({ backTo, backLabel }) {
  const { user } = useAuth()
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
            <LangToggle />
            <ThemeToggle />
            {user ? (
              <>
                <span className="who wide-only">
                  <span className="visually-hidden">{t('app.signedIn', { name: user.name })}</span>
                  <span aria-hidden="true">{user.name}</span>
                </span>
                <Link to="/app/speak" className="nav-link wide-only" viewTransition={!reducedMotion()}>
                  {t('nav.openApp')}
                </Link>
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
