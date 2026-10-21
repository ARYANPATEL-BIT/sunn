import { ArrowLeft, ArrowRight, AudioLines, BookOpen, Check, CheckCircle2, Mic, Sparkles, Volume2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { isOnboarded, setOnboarded } from './prefs.js'
import { Alert, Pill, useGo } from './ui.jsx'

const TOTAL_STEPS = 4

export default function Onboarding() {
  const { user } = useAuth()
  const { lang, setLang, t } = useLang()
  const go = useGo()

  const [step, setStep] = useState(1)
  const [phrases, setPhrases] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [seeding, setSeeding] = useState(false)

  const hasPhrases = phrases && phrases.length > 0
  const enrolledCount = phrases ? phrases.filter((p) => (p.enrolled ?? 0) >= 3).length : 0
  const needCount = phrases ? phrases.filter((p) => (p.enrolled ?? 0) < 3).length : 0

  const handleLoadDefaults = async () => {
    setSeeding(true)
    setError(null)
    try {
      const data = await api.loadDefaultPhrases()
      setPhrases(data)
    } catch (err) {
      setError(err)
    } finally {
      setSeeding(false)
    }
  }

  const handleLanguageSelect = async (code) => {
    if (code === lang) return
    setLang(code)
    try {
      await api.updateMe({ language: code })
    } catch {
      // Non-blocking
    }
  }

  useEffect(() => {
    let active = true
    api
      .listPhrases()
      .then((data) => {
        if (active) setPhrases(data)
      })
      .catch((err) => {
        if (active) setError(err)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const handleFinish = (targetPath = '/app/speak') => {
    if (user?.id) {
      setOnboarded(user.id, true)
    }
    go(targetPath, { replace: true })
  }

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        handleFinish('/app/speak')
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [user?.id])

  const handleNext = () => {
    if (step < TOTAL_STEPS) {
      setStep((s) => s + 1)
    } else {
      if (hasPhrases && enrolledCount === 0) {
        handleFinish('/app/enroll')
      } else {
        handleFinish('/app/speak')
      }
    }
  }

  const handleBack = () => {
    if (step > 1) {
      setStep((s) => s - 1)
    }
  }

  return (
    <section className="screen onboarding-screen">
      <header className="onboarding-header">
        <div
          className="onboarding-step-indicator"
          aria-label={t('onboarding.stepProgress', { current: step, total: TOTAL_STEPS })}
        >
          <div className="step-dots" aria-hidden="true">
            {Array.from({ length: TOTAL_STEPS }, (_, i) => (
              <span
                key={i}
                className={`step-dot ${i + 1 === step ? 'active' : i + 1 < step ? 'done' : ''}`}
              />
            ))}
          </div>
          <span className="step-pill">
            {t('onboarding.stepProgress', { current: step, total: TOTAL_STEPS })}
          </span>
          <button type="button" className="pill-outline skip-btn" onClick={() => handleFinish('/app/speak')}>
            {t('onboarding.skip')}
          </button>
        </div>
      </header>

      <Alert error={error} />

      {/* Screen reader step announcement */}
      <div className="visually-hidden" aria-live="polite">
        {t('onboarding.stepProgress', { current: step, total: TOTAL_STEPS })}
      </div>

      <div className="onboarding-step-container">
        {step === 1 && (
          <article className="step-card" aria-labelledby="step1-title">
            <h1 id="step1-title">{t('onboarding.welcomeHeading')}</h1>
            <p className="step-desc">{t('onboarding.welcomeBody')}</p>

            <div className="features-grid">
              <div className="feature-item">
                <BookOpen className="feature-icon" size={24} aria-hidden="true" strokeWidth={1.5} />
                <div className="feature-text">
                  <strong>{t('onboarding.featurePhrasesTitle')}</strong>
                  <p className="muted">{t('onboarding.featurePhrasesDesc')}</p>
                </div>
              </div>

              <div className="feature-item">
                <Volume2 className="feature-icon" size={24} aria-hidden="true" strokeWidth={1.5} />
                <div className="feature-text">
                  <strong>{t('onboarding.featureVoiceTitle')}</strong>
                  <p className="muted">{t('onboarding.featureVoiceDesc')}</p>
                </div>
              </div>
            </div>
          </article>
        )}

        {step === 2 && (
          <article className="step-card" aria-labelledby="step2-title">
            <h1 id="step2-title">{t('onboarding.langHeading')}</h1>
            <p className="step-desc">{t('onboarding.langDesc')}</p>

            <div className="choice-cards-grid" role="radiogroup" aria-label={t('onboarding.langHeading')}>
              {[
                ['hi', 'onboarding.langHindi', 'नमस्ते'],
                ['en', 'onboarding.langEnglish', 'Hello'],
              ].map(([code, labelKey, sampleGreeting]) => {
                const isSelected = lang === code
                return (
                  <button
                    key={code}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    className={`choice-card ${isSelected ? 'active' : ''}`}
                    onClick={() => handleLanguageSelect(code)}
                  >
                    <div className="choice-card-content">
                      <span className="choice-greeting">{sampleGreeting}</span>
                      <strong className="choice-label">{t(labelKey)}</strong>
                    </div>
                    {isSelected && <Check className="choice-check" size={20} aria-hidden="true" strokeWidth={2} />}
                  </button>
                )
              })}
            </div>
          </article>
        )}

        {step === 3 && (
          <article className="step-card" aria-labelledby="step3-title">
            <h1 id="step3-title">{t('onboarding.howHeading')}</h1>
            <p className="step-desc">{t('onboarding.howDesc')}</p>

            <div className="workflow-steps">
              <div className="workflow-item">
                <span className="step-number" aria-hidden="true">
                  1
                </span>
                <div className="workflow-content">
                  <p>{t('onboarding.howStep1')}</p>
                </div>
              </div>

              <div className="workflow-item">
                <span className="step-number" aria-hidden="true">
                  2
                </span>
                <div className="workflow-content">
                  <p>{t('onboarding.howStep2')}</p>
                </div>
              </div>

              <div className="workflow-item">
                <span className="step-number" aria-hidden="true">
                  3
                </span>
                <div className="workflow-content">
                  <p>{t('onboarding.howStep3')}</p>
                </div>
              </div>
            </div>
          </article>
        )}

        {step === 4 && (
          <article className="step-card setup-readiness-card" aria-labelledby="step4-title">
            <h1 id="step4-title">{t('onboarding.setupHeading')}</h1>

            {enrolledCount > 0 ? (
              <div className="readiness-state ready">
                <CheckCircle2 className="readiness-icon" size={32} aria-hidden="true" strokeWidth={1.5} />
                <h2>{t('onboarding.setupReadyTitle')}</h2>
                <p className="muted">{t('onboarding.setupReadyDesc')}</p>
                <div className="readiness-meta">
                  <span className="summary-pill">{t('phrases.total', { count: phrases.length })}</span>
                </div>
              </div>
            ) : hasPhrases ? (
              <div className="readiness-state need-teaching">
                <Mic className="readiness-icon" size={32} aria-hidden="true" strokeWidth={1.5} />
                <h2>{t('onboarding.setupNeedTitle')}</h2>
                <p className="muted">{t('onboarding.setupNeedDesc')}</p>
                <div className="readiness-actions">
                  <button type="button" className="pill-outline" onClick={() => handleFinish('/app/enroll')}>
                    <Mic size={16} aria-hidden="true" strokeWidth={1.5} />
                    <span>{t('onboarding.goTeach')}</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="readiness-state empty">
                <BookOpen className="readiness-icon" size={32} aria-hidden="true" strokeWidth={1.5} />
                <h2>{t('onboarding.setupEmptyTitle')}</h2>
                <p className="muted">{t('onboarding.setupEmptyDesc')}</p>
                <div className="readiness-actions">
                  <Pill onClick={handleLoadDefaults} disabled={seeding} icon={null} arrow={false}>
                    {t(seeding ? 'onboarding.addingDefaults' : 'onboarding.addDefaults')}
                  </Pill>
                  <button type="button" className="pill-outline" onClick={() => handleFinish('/app/phrases')}>
                    <span>{t('onboarding.goLibrary')}</span>
                  </button>
                </div>
              </div>
            )}
          </article>
        )}
      </div>

      <footer className="onboarding-footer">
        {step > 1 && (
          <button type="button" className="pill-outline" onClick={handleBack}>
            <ArrowLeft size={16} aria-hidden="true" strokeWidth={1.5} />
            <span>{t('onboarding.back')}</span>
          </button>
        )}
        <Pill onClick={handleNext} arrow={step < TOTAL_STEPS}>
          {t(step === TOTAL_STEPS ? 'onboarding.finish' : 'onboarding.next')}
        </Pill>
      </footer>
    </section>
  )
}
