import { useCallback, useEffect, useRef, useState } from 'react'
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
    targetSelector: '.phrases-list, .phrase-card, .phrases-search, .phrases-screen',
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
    targetSelector: '[aria-labelledby="heading-accessibility"], #heading-accessibility, .settings-screen .group-wrap, .settings-screen',
  },
  {
    id: 'progress',
    path: '/app/progress',
    shortKey: 'presenter.stepShort_5',
    titleKey: 'presenter.stepProgressTitle',
    cueKey: 'presenter.stepProgressCue',
    targetSelector: '[aria-labelledby="heading-overview"], .chart, #your-data, .progress-screen',
  },
]

export default function PresenterBar({ onClose }) {
  const { t } = useLang()
  const location = useLocation()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(false)
  const [completed, setCompleted] = useState(false)

  // Step 1 (index 0) is always the starting state on fresh launch
  const [stepIndex, setStepIndex] = useState(0)
  const freshLaunchRef = useRef(true)

  // Side positioning state
  const [placement, setPlacement] = useState('left')
  const [cardStyle, setCardStyle] = useState({})
  const cardRef = useRef(null)

  // Spotlight target reference
  const highlightedRef = useRef(null)

  // On mount: explicitly lock to Step 1 and navigate to /app/onboarding
  useEffect(() => {
    setStepIndex(0)
    setCompleted(false)
    navigate(DEMO_STEPS[0].path, { replace: true })
    const timer = setTimeout(() => {
      freshLaunchRef.current = false
    }, 400)
    return () => clearTimeout(timer)
  }, [navigate])

  // Sync step only when user navigates routes after the fresh launch window
  useEffect(() => {
    if (freshLaunchRef.current) return
    const matched = DEMO_STEPS.findIndex((s) => location.pathname.startsWith(s.path))
    if (matched >= 0 && matched !== stepIndex) {
      setStepIndex(matched)
      setCompleted(false)
    }
  }, [location.pathname, stepIndex])

  const currentStep = DEMO_STEPS[stepIndex]

  // Intelligent side positioning calculation
  const updatePosition = useCallback(() => {
    if (typeof window === 'undefined') return
    const width = window.innerWidth
    const height = window.innerHeight

    // Narrow / mobile viewports (< 1040px): bottom sheet mode
    if (width < 1040) {
      setPlacement('bottom')
      setCardStyle({})
      return
    }

    const target = document.querySelector(currentStep.targetSelector)
    const cardEl = cardRef.current
    const cardHeight = cardEl ? cardEl.offsetHeight : 320
    const cardWidth = 320
    const margin = 20

    if (target) {
      const rect = target.getBoundingClientRect()
      const leftSpace = rect.left
      const rightSpace = width - rect.right

      let top = Math.max(76, rect.top)
      const maxTop = height - cardHeight - margin
      if (top > maxTop) top = Math.max(76, maxTop)

      // Prefer left side if there is sufficient margin
      if (leftSpace >= cardWidth + margin * 2) {
        const left = Math.max(margin, (leftSpace - cardWidth) / 2)
        setPlacement('left')
        setCardStyle({
          position: 'fixed',
          top: `${Math.round(top)}px`,
          left: `${Math.round(left)}px`,
          right: 'auto',
          bottom: 'auto',
        })
      } else if (rightSpace >= cardWidth + margin * 2) {
        // Use right side if left is too narrow
        const right = Math.max(margin, (rightSpace - cardWidth) / 2)
        setPlacement('right')
        setCardStyle({
          position: 'fixed',
          top: `${Math.round(top)}px`,
          right: `${Math.round(right)}px`,
          left: 'auto',
          bottom: 'auto',
        })
      } else {
        // Fallback for compact desktop viewports
        if (width >= 960) {
          setPlacement('left')
          setCardStyle({
            position: 'fixed',
            top: `${Math.round(top)}px`,
            left: `${margin}px`,
            right: 'auto',
            bottom: 'auto',
          })
        } else {
          setPlacement('bottom')
          setCardStyle({})
        }
      }
    } else {
      // Fallback when target is not yet in DOM
      setPlacement('left')
      setCardStyle({
        position: 'fixed',
        top: '80px',
        left: `${margin}px`,
        right: 'auto',
        bottom: 'auto',
      })
    }
  }, [currentStep.targetSelector])

  // Navigate to step
  function goToStep(index) {
    if (index >= 0 && index < DEMO_STEPS.length) {
      freshLaunchRef.current = false
      setCompleted(false)
      setStepIndex(index)
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
    freshLaunchRef.current = true
    setCompleted(false)
    setStepIndex(0)
    navigate(DEMO_STEPS[0].path, { viewTransition: !reducedMotion() })
    setTimeout(() => {
      freshLaunchRef.current = false
    }, 400)
  }

  // Highlight and scroll target into view
  useEffect(() => {
    if (highlightedRef.current) {
      highlightedRef.current.classList.remove('presenter-target-highlight')
      highlightedRef.current = null
    }

    if (completed || collapsed) {
      updatePosition()
      return
    }

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
      updatePosition()
    }, 150)

    return () => {
      clearTimeout(timer)
      if (highlightedRef.current) {
        highlightedRef.current.classList.remove('presenter-target-highlight')
        highlightedRef.current = null
      }
    }
  }, [location.pathname, stepIndex, completed, collapsed, currentStep.targetSelector, updatePosition])

  // Recalculate position on resize and scroll
  useEffect(() => {
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, { passive: true })
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition)
    }
  }, [updatePosition])

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
      ref={cardRef}
      className={`presenter-tour-card presenter-bar ${placement} ${collapsed ? 'collapsed' : ''} ${completed ? 'completed-view' : ''}`}
      aria-label={t('presenter.title')}
      role="region"
      style={cardStyle}
    >
      {/* Tour Card Header */}
      <div className="presenter-card-header presenter-bar-header">
        <div className="presenter-brand presenter-title-wrap">
          <Icon name="presentation" className="presenter-brand-icon presenter-icon" />
          <span className="presenter-brand-title presenter-heading">{t('presenter.title')}</span>
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
            <Icon name={collapsed ? 'chevronUp' : 'chevronDown'} />
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
        <div className="presenter-card-body presenter-bar-body">
          {/* Step indicator and progress meter */}
          <div className="presenter-step-meta">
            <span className="presenter-step-pill presenter-step-badge">
              {t('presenter.stepIndicator', {
                current: stepIndex + 1,
                total: DEMO_STEPS.length,
              })}
            </span>

            <div className="presenter-segment-meter presenter-mobile-progress" aria-hidden="true">
              {DEMO_STEPS.map((step, idx) => (
                <span
                  key={step.id}
                  className={`presenter-segment presenter-dot ${idx === stepIndex ? 'active' : ''} ${idx < stepIndex ? 'completed' : ''}`}
                />
              ))}
            </div>
          </div>

          {/* Current Step Content */}
          <div className="presenter-step-content presenter-cue-card">
            <h2 className="presenter-step-heading presenter-cue-title">{t(currentStep.titleKey)}</h2>
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
              className="presenter-action-btn subtle"
              onClick={handleRestart}
              title={t('presenter.restart')}
              aria-label={t('presenter.restart')}
            >
              <Icon name="rotate" />
              <span>{t('presenter.restart')}</span>
            </button>

            <div className="presenter-nav-buttons presenter-prev-next">
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

          <div className="presenter-keyboard-hint wide-only">
            {t('presenter.keyboardHint')}
          </div>
        </div>
      )}

      {/* Completed celebration view */}
      {!collapsed && completed && (
        <div className="presenter-card-body presenter-bar-body presenter-completed-body">
          <div className="presenter-completed-card">
            <Icon name="checkCircle" className="presenter-completed-icon" />
            <h2 className="presenter-completed-title">{t('presenter.completedTitle')}</h2>
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
              className="presenter-action-btn subtle"
              onClick={handleRestart}
              title={t('presenter.restart')}
              aria-label={t('presenter.restart')}
            >
              <Icon name="rotate" />
              <span>{t('presenter.restart')}</span>
            </button>

            <div className="presenter-nav-buttons presenter-prev-next">
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
