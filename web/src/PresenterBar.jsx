import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useLang } from './i18n/index.jsx'
import { Icon, reducedMotion } from './ui/index.js'

export const DEMO_STEPS = [
  {
    id: 'onboarding',
    path: '/app/onboarding',
    titleKey: 'presenter.stepOnboardingTitle',
    cueKey: 'presenter.stepOnboardingCue',
  },
  {
    id: 'phrases',
    path: '/app/phrases',
    titleKey: 'presenter.stepPhrasesTitle',
    cueKey: 'presenter.stepPhrasesCue',
  },
  {
    id: 'speak',
    path: '/app/speak',
    titleKey: 'presenter.stepSpeakTitle',
    cueKey: 'presenter.stepSpeakCue',
  },
  {
    id: 'settings',
    path: '/app/settings',
    titleKey: 'presenter.stepSettingsTitle',
    cueKey: 'presenter.stepSettingsCue',
  },
  {
    id: 'progress',
    path: '/app/progress',
    titleKey: 'presenter.stepProgressTitle',
    cueKey: 'presenter.stepProgressCue',
  },
]

export default function PresenterBar({ onClose }) {
  const { t } = useLang()
  const location = useLocation()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(false)

  const activeIndex = DEMO_STEPS.findIndex((s) => location.pathname.startsWith(s.path))
  const currentStep = DEMO_STEPS[activeIndex >= 0 ? activeIndex : 2] // Default to Speak step if in general area

  function goToStep(index) {
    if (index >= 0 && index < DEMO_STEPS.length) {
      navigate(DEMO_STEPS[index].path, { viewTransition: !reducedMotion() })
    }
  }

  function handlePrev() {
    if (activeIndex > 0) goToStep(activeIndex - 1)
  }

  function handleNext() {
    if (activeIndex >= 0 && activeIndex < DEMO_STEPS.length - 1) {
      goToStep(activeIndex + 1)
    }
  }

  function handleRestart() {
    goToStep(0)
  }

  return (
    <aside
      className={`presenter-bar ${collapsed ? 'collapsed' : ''}`}
      aria-label={t('presenter.title')}
      role="region"
    >
      <div className="presenter-bar-header">
        <div className="presenter-title-wrap">
          <Icon name="presentation" className="presenter-icon" />
          <span className="presenter-heading">{t('presenter.title')}</span>
          <span className="presenter-step-badge">
            {t('presenter.stepIndicator', {
              current: activeIndex >= 0 ? activeIndex + 1 : '-',
              total: DEMO_STEPS.length,
            })}
          </span>
        </div>

        <div className="presenter-header-actions">
          <button
            type="button"
            className="presenter-icon-btn"
            onClick={() => setCollapsed(!collapsed)}
            aria-expanded={!collapsed}
            title={collapsed ? t('presenter.expand') : t('presenter.collapse')}
            aria-label={collapsed ? t('presenter.expand') : t('presenter.collapse')}
          >
            <Icon name={collapsed ? 'chevronDown' : 'chevronUp'} />
          </button>
          <button
            type="button"
            className="presenter-icon-btn"
            onClick={onClose}
            title={t('presenter.exit')}
            aria-label={t('presenter.exit')}
          >
            <Icon name="x" />
          </button>
        </div>
      </div>

      {!collapsed && (
        <div className="presenter-bar-body">
          <nav className="presenter-step-pills" aria-label={t('presenter.navAria')}>
            {DEMO_STEPS.map((step, idx) => {
              const isCurrent = idx === activeIndex
              const isPast = activeIndex >= 0 && idx < activeIndex
              return (
                <button
                  key={step.id}
                  type="button"
                  className={`presenter-step ${isCurrent ? 'active' : ''} ${isPast ? 'completed' : ''}`}
                  onClick={() => goToStep(idx)}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  {isPast ? (
                    <Icon name="check" className="presenter-step-icon" />
                  ) : (
                    <span className="presenter-step-num">{idx + 1}</span>
                  )}
                  <span className="presenter-step-text">{t(step.titleKey)}</span>
                </button>
              )
            })}
          </nav>

          <div className="presenter-cue-card">
            <div className="presenter-cue-header">
              <Icon name="idea" className="presenter-cue-icon" />
              <strong className="presenter-cue-title">{t(currentStep.titleKey)}</strong>
            </div>
            <p className="presenter-cue-text">{t(currentStep.cueKey)}</p>
          </div>

          <div className="presenter-actions-row">
            <button
              type="button"
              className="presenter-action-btn"
              onClick={handleRestart}
              title={t('presenter.restart')}
            >
              <Icon name="rotate" />
              <span>{t('presenter.restart')}</span>
            </button>

            <div className="presenter-prev-next">
              <button
                type="button"
                className="presenter-action-btn"
                onClick={handlePrev}
                disabled={activeIndex <= 0}
                aria-label={t('presenter.prev')}
              >
                <Icon name="chevronLeft" />
                <span>{t('presenter.prev')}</span>
              </button>
              <button
                type="button"
                className="presenter-action-btn primary"
                onClick={handleNext}
                disabled={activeIndex >= DEMO_STEPS.length - 1}
                aria-label={t('presenter.next')}
              >
                <span>{t('presenter.next')}</span>
                <Icon name="chevronRight" />
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
