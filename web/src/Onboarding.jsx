import { useEffect, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { LANGUAGES } from './i18n/languages.js'
import { setOnboarded } from './prefs.js'
import { speakProgress } from './quickstart.js'
import { Alert, Button, Icon, PrimaryButton, useGo } from './ui/index.js'
import { LanguageSub } from './ui/LanguagePicker.jsx'

const TOTAL_STEPS = 4

export default function Onboarding() {
  const { user } = useAuth()
  const { lang, setLang, t } = useLang()
  const go = useGo()

  const [step, setStep] = useState(1)
  const [phrases, setPhrases] = useState(null)
  const [error, setError] = useState(null)
  const [seeding, setSeeding] = useState(false)

  const hasPhrases = phrases && phrases.length > 0
  // Ready means Speak is open: the quick-start phrases recorded in the language spoken now.
  const ready = hasPhrases && speakProgress(phrases, user.language).open

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

  // The screen's language only, on this device. The language the user speaks is set at sign-up
  // and changed in Settings, which warns first: changing it makes old recordings stop counting.
  const handleLanguageSelect = (code) => {
    if (code !== lang) setLang(code)
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
      if (hasPhrases && !ready) {
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
    <section className="screen onboarding">
      <header className="onboarding-top">
        <div className="step-meter" aria-hidden="true">
          {Array.from({ length: TOTAL_STEPS }, (_, i) => (
            <span key={i} className={`segment ${i + 1 <= step ? 'on' : ''}`} />
          ))}
        </div>
        <span className="step-count">{t('onboarding.stepProgress', { current: step, total: TOTAL_STEPS })}</span>
        <button type="button" className="text-button" onClick={() => handleFinish('/app/speak')}>
          {t('onboarding.skip')}
        </button>
      </header>

      <Alert error={error} />

      {/* Screen reader step announcement */}
      <div className="visually-hidden" aria-live="polite">
        {t('onboarding.stepProgress', { current: step, total: TOTAL_STEPS })}
      </div>

      <div className="onboarding-step" key={step}>
        {step === 1 && (
          <article aria-labelledby="step1-title">
            <h1 id="step1-title" className="large-title">
              {t('onboarding.welcomeHeading')}
            </h1>
            <p className="lede-sm">{t('onboarding.welcomeBody')}</p>
            <ul className="group">
              <li className="row">
                <Icon name="book" className="row-icon" />
                <span className="row-text">
                  <strong className="row-title">{t('onboarding.featurePhrasesTitle')}</strong>
                  <span className="row-sub">{t('onboarding.featurePhrasesDesc')}</span>
                </span>
              </li>
              <li className="row">
                <Icon name="volume" className="row-icon" />
                <span className="row-text">
                  <strong className="row-title">{t('onboarding.featureVoiceTitle')}</strong>
                  <span className="row-sub">{t('onboarding.featureVoiceDesc')}</span>
                </span>
              </li>
            </ul>
          </article>
        )}

        {step === 2 && (
          <article aria-labelledby="step2-title">
            <h1 id="step2-title" className="large-title">
              {t('onboarding.langHeading')}
            </h1>
            <p className="lede-sm">{t('onboarding.langDesc')}</p>
            <div className="group" role="radiogroup" aria-label={t('onboarding.langHeading')}>
              {LANGUAGES.map(({ code, native }) => (
                <button
                  key={code}
                  type="button"
                  role="radio"
                  aria-checked={lang === code}
                  className="row choice"
                  onClick={() => handleLanguageSelect(code)}
                >
                  <span className="row-text">
                    <span className="greeting" lang={code}>
                      {native}
                    </span>
                    <span className="row-sub">
                      <LanguageSub code={code} />
                    </span>
                  </span>
                  <Icon name="check" className="choice-check" />
                </button>
              ))}
            </div>
          </article>
        )}

        {step === 3 && (
          <article aria-labelledby="step3-title">
            <h1 id="step3-title" className="large-title">
              {t('onboarding.howHeading')}
            </h1>
            <p className="lede-sm">{t('onboarding.howDesc')}</p>
            <ol className="group">
              {['onboarding.howStep1', 'onboarding.howStep2', 'onboarding.howStep3'].map((key, i) => (
                <li key={key} className="row">
                  <span className="step-n" aria-hidden="true">
                    {i + 1}
                  </span>
                  <span className="row-text">
                    <span className="row-title">{t(key)}</span>
                  </span>
                </li>
              ))}
            </ol>
          </article>
        )}

        {step === 4 && (
          <article aria-labelledby="step4-title">
            <h1 id="step4-title" className="large-title">
              {t('onboarding.setupHeading')}
            </h1>

            {ready ? (
              <div className="status-card">
                <Icon name="checkCircle" className="status-icon success" />
                <h2>{t('onboarding.setupReadyTitle')}</h2>
                <p>{t('onboarding.setupReadyDesc')}</p>
                <p className="status-meta">{t('phrases.total', { count: phrases.length })}</p>
              </div>
            ) : hasPhrases ? (
              <div className="status-card">
                <Icon name="mic" className="status-icon" />
                <h2>{t('onboarding.setupNeedTitle')}</h2>
                <p>{t('onboarding.setupNeedDesc')}</p>
                <div className="actions">
                  <Button icon="mic" onClick={() => handleFinish('/app/enroll')}>
                    {t('onboarding.goTeach')}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="status-card">
                <Icon name="book" className="status-icon" />
                <h2>{t('onboarding.setupEmptyTitle')}</h2>
                <p>{t('onboarding.setupEmptyDesc')}</p>
                <div className="actions">
                  <Button onClick={handleLoadDefaults} disabled={seeding}>
                    {t(seeding ? 'onboarding.addingDefaults' : 'onboarding.addDefaults')}
                  </Button>
                  <Button onClick={() => handleFinish('/app/phrases')}>{t('onboarding.goLibrary')}</Button>
                </div>
              </div>
            )}
          </article>
        )}
      </div>

      <footer className="onboarding-actions">
        {step > 1 && (
          <Button icon="arrowLeft" onClick={handleBack}>
            {t('onboarding.back')}
          </Button>
        )}
        <PrimaryButton onClick={handleNext}>{t(step === TOTAL_STEPS ? 'onboarding.finish' : 'onboarding.next')}</PrimaryButton>
      </footer>
    </section>
  )
}
