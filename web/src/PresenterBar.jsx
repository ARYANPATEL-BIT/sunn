import {
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Lightbulb,
  Presentation,
  RotateCcw,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useLang } from './i18n/index.jsx'
import { reducedMotion } from './ui.jsx'

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
          <Presentation size={18} aria-hidden="true" className="presenter-icon" />
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
            {collapsed ? <ChevronDown size={18} aria-hidden="true" /> : <ChevronUp size={18} aria-hidden="true" />}
          </button>
          <button
            type="button"
            className="presenter-icon-btn"
            onClick={onClose}
            title={t('presenter.exit')}
            aria-label={t('presenter.exit')}
          >
            <X size={18} aria-hidden="true" />
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
                  className={`presenter-pill ${isCurrent ? 'active' : ''} ${isPast ? 'completed' : ''}`}
                  onClick={() => goToStep(idx)}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  {isPast ? (
                    <CheckCircle2 size={14} aria-hidden="true" className="presenter-pill-icon" />
                  ) : (
                    <span className="presenter-pill-num">{idx + 1}</span>
                  )}
                  <span className="presenter-pill-text">{t(step.titleKey)}</span>
                </button>
              )
            })}
          </nav>

          <div className="presenter-cue-card">
            <div className="presenter-cue-header">
              <Lightbulb size={16} aria-hidden="true" className="presenter-cue-icon" />
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
              <RotateCcw size={14} aria-hidden="true" />
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
                <ChevronLeft size={16} aria-hidden="true" />
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
                <ChevronRight size={16} aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
