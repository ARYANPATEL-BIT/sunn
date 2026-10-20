import { ArrowLeft, ArrowRight, BookOpen, Check, Sparkles, Volume2 } from 'lucide-react'
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

  const handleNext = () => {
    if (step < TOTAL_STEPS) {
      setStep((s) => s + 1)
    } else {
      handleFinish('/app/speak')
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
          <span className="step-pill">
            {t('onboarding.stepProgress', { current: step, total: TOTAL_STEPS })}
          </span>
          <button type="button" className="pill-outline skip-btn" onClick={() => handleFinish('/app/speak')}>
            {t('onboarding.skip')}
          </button>
        </div>
      </header>

      <Alert error={error} />

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
