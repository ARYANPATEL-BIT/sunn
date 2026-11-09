import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useLang } from './i18n/index.jsx'
import { Icon, reducedMotion } from './ui/index.js'

export const DEMO_STEPS = [
  {
    id: 'onboarding',
    path: '/app/onboarding',
    shortKey: 'presenter.stepShort_1',
    titleKey: 'presenter.stepOnboardingTitle',
    cueKey: 'presenter.stepOnboardingCue',
    targetSelector: '.onboarding-step, .onboarding, .screen',
  },
  {
    id: 'phrases',
    path: '/app/phrases',
    shortKey: 'presenter.stepShort_2',
    titleKey: 'presenter.stepPhrasesTitle',
    cueKey: 'presenter.stepPhrasesCue',
    targetSelector: '.phrases-search, .phrase-card, .screen-header, .phrases-screen',
  },
  {
    id: 'speak',
    path: '/app/speak',
    shortKey: 'presenter.stepShort_3',
    titleKey: 'presenter.stepSpeakTitle',
    cueKey: 'presenter.stepSpeakCue',
    targetSelector: '.speak-device, .push-button, .readout, .speak',
  },
  {
    id: 'settings',
    path: '/app/settings',
    shortKey: 'presenter.stepShort_4',
    titleKey: 'presenter.stepSettingsTitle',
    cueKey: 'presenter.stepSettingsCue',
    targetSelector: '#heading-accessibility, [aria-labelledby="heading-accessibility"], .settings-screen .group-wrap, .settings-screen',
  },
  {
    id: 'progress',
    path: '/app/progress',
    shortKey: 'presenter.stepShort_5',
    titleKey: 'presenter.stepProgressTitle',
    cueKey: 'presenter.stepProgressCue',
    targetSelector: '.chart, [aria-labelledby="heading-overview"], #your-data, .progress-screen',
  },
]

export default function PresenterBar({ onClose }) {
  const { t } = useLang()
  const location = useLocation()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(false)
  const [completed, setCompleted] = useState(false)

  // Find step from current location, default to 0 (Step 1)
  const activeIndex = DEMO_STEPS.findIndex((s) => location.pathname.startsWith(s.path))
  const stepIndex = activeIndex >= 0 ? activeIndex : 0
  const currentStep = DEMO_STEPS[stepIndex]

  // Spotlight target reference
  const highlightedRef = useRef(null)

  // Navigate to step
  function goToStep(index) {
    if (index >= 0 && index < DEMO_STEPS.length) {
      setCompleted(false)
      navigate(DEMO_STEPS[index].path, { viewTransition: !reducedMotion() })
    }
  }

  function handlePrev() {
    if (completed) {
      setCompleted(false)
      goToStep(DEMO_STEPS.length - 1)
    } else if (stepIndex > 0) {
      goToStep(stepIndex - 1)
    }
  }

  function handleNext() {
    if (stepIndex < DEMO_STEPS.length - 1) {
      goToStep(stepIndex + 1)
    } else {
      setCompleted(true)
    }
  }

  function handleRestart() {
    setCompleted(false)
    goToStep(0)
  }

  // Highlight effect
  useEffect(() => {
    if (highlightedRef.current) {
      highlightedRef.current.classList.remove('presenter-target-highlight')
      highlightedRef.current = null
    }

    if (completed || collapsed) return

    const timer = setTimeout(() => {
      const target = document.querySelector(currentStep.targetSelector)
      if (target) {
        target.classList.add('presenter-target-highlight')
        highlightedRef.current = target
        try {
          target.scrollIntoView({
            behavior: reducedMotion() ? 'auto' : 'smooth',
            block: 'center',
          })
        } catch {
          // ignore scroll errors
        }
      }
    }, 150)

    return () => {
      clearTimeout(timer)
      if (highlightedRef.current) {
        highlightedRef.current.classList.remove('presenter-target-highlight')
        highlightedRef.current = null
      }
    }
  }, [location.pathname, stepIndex, completed, collapsed, currentStep.targetSelector])

  // Keyboard navigation
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose?.()
      } else if (e.key === 'ArrowRight' && !e.target.matches('input, textarea, select')) {
        e.preventDefault()
        handleNext()
      } else if (e.key === 'ArrowLeft' && !e.target.matches('input, textarea, select')) {
        e.preventDefault()
        handlePrev()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  })

  return (
    <aside
      className={`presenter-bar ${collapsed ? 'collapsed' : ''} ${completed ? 'completed-view' : ''}`}
      aria-label={t('presenter.title')}
      role="region"
    >
      <div className="presenter-bar-header">
        <div className="presenter-title-wrap">
          <Icon name="presentation" className="presenter-icon" />
          <span className="presenter-heading">{t('presenter.title')}</span>
          <span className="presenter-step-badge">
            {completed
              ? t('presenter.finish')
              : t('presenter.stepIndicator', {
                  current: stepIndex + 1,
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

      {/* Collapsed minimal state */}
      {collapsed && (
        <div className="presenter-collapsed-row">
          <span className="presenter-collapsed-label">
            {completed
              ? t('presenter.completedTitle')
              : `${t('presenter.stepIndicator', { current: stepIndex + 1, total: DEMO_STEPS.length })}: ${t(currentStep.shortKey)}`}
          </span>
        </div>
      )}

      {/* Expanded Walkthrough state */}
      {!collapsed && !completed && (
        <div className="presenter-bar-body">
          {/* Desktop step pills */}
          <nav className="presenter-step-pills wide-stepper" aria-label={t('presenter.navAria')}>
            {DEMO_STEPS.map((step, idx) => {
              const isCurrent = idx === stepIndex
              const isPast = idx < stepIndex
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
                  <span className="presenter-step-text">{t(step.shortKey)}</span>
                </button>
              )
            })}
          </nav>

          {/* Mobile step progress indicator */}
          <div className="presenter-mobile-progress" aria-hidden="true">
            <div className="presenter-progress-dots">
              {DEMO_STEPS.map((step, idx) => (
                <span
                  key={step.id}
                  className={`presenter-dot ${idx === stepIndex ? 'active' : ''} ${idx < stepIndex ? 'completed' : ''}`}
                />
              ))}
            </div>
            <span className="presenter-mobile-title">{t(currentStep.shortKey)}</span>
          </div>

          {/* Cue card */}
          <div className="presenter-cue-card">
            <div className="presenter-cue-header">
              <Icon name="idea" className="presenter-cue-icon" />
              <strong className="presenter-cue-title">{t(currentStep.titleKey)}</strong>
            </div>
            <p className="presenter-cue-text">{t(currentStep.cueKey)}</p>
            <div className="presenter-hint">
              <Icon name="eye" className="presenter-hint-icon" />
              <span>{t('presenter.interactiveHint')}</span>
            </div>
          </div>

          {/* Actions row */}
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

            <span className="presenter-keyboard-hint wide-only">
              {t('presenter.keyboardHint')}
            </span>

            <div className="presenter-prev-next">
              <button
                type="button"
                className="presenter-action-btn"
                onClick={handlePrev}
                disabled={stepIndex <= 0}
                aria-label={t('presenter.prev')}
              >
                <Icon name="chevronLeft" />
                <span>{t('presenter.prev')}</span>
              </button>
              <button
                type="button"
                className="presenter-action-btn primary"
                onClick={handleNext}
                aria-label={stepIndex >= DEMO_STEPS.length - 1 ? t('presenter.finish') : t('presenter.next')}
              >
                <span>{stepIndex >= DEMO_STEPS.length - 1 ? t('presenter.finish') : t('presenter.next')}</span>
                <Icon name={stepIndex >= DEMO_STEPS.length - 1 ? 'check' : 'chevronRight'} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Completed celebration view */}
      {!collapsed && completed && (
        <div className="presenter-bar-body presenter-completed-body">
          <div className="presenter-completed-card">
            <div className="presenter-completed-header">
              <Icon name="checkCircle" className="presenter-completed-icon" />
              <h2 className="presenter-completed-title">{t('presenter.completedTitle')}</h2>
            </div>
            <p className="presenter-completed-text">{t('presenter.completedDesc')}</p>

            <div className="presenter-completed-steps">
              {DEMO_STEPS.map((step) => (
                <div key={step.id} className="presenter-completed-chip">
                  <Icon name="check" className="presenter-chip-check" />
                  <span>{t(step.shortKey)}</span>
                </div>
              ))}
            </div>
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
                aria-label={t('presenter.prev')}
              >
                <Icon name="chevronLeft" />
                <span>{t('presenter.prev')}</span>
              </button>
              <button
                type="button"
                className="presenter-action-btn primary"
                onClick={onClose}
                aria-label={t('presenter.exit')}
              >
                <Icon name="check" />
                <span>{t('presenter.finish')}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
