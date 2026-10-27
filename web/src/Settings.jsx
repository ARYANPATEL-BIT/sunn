import {
  BookOpen,
  Check,
  CheckCircle2,
  ExternalLink,
  Languages,
  Phone,
  Shield,
  Square,
  Trash2,
  Type,
  Upload,
  Volume2,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { applyPreferences, getPreferences, setPreference } from './prefs.js'
import { Alert, Pill, useGo } from './ui.jsx'

export default function Settings() {
  const { user, signedIn, deleteAccount } = useAuth()
  const { lang, setLang, t } = useLang()
  const go = useGo()

  const [prefs, setPrefs] = useState(getPreferences)
  const [caregiverName, setCaregiverName] = useState(user?.caregiver_name || '')
  const [caregiverPhone, setCaregiverPhone] = useState(user?.caregiver_phone || '')

  const [busy, setBusy] = useState(null) // 'caregiver' | 'voice' | 'upload' | 'language' | 'account'
  const [playingSample, setPlayingSample] = useState(false)
  const [confirmSpeak, setConfirmSpeak] = useState(null) // the language the user asked to speak
  const [voiceFile, setVoiceFile] = useState(null)
  const [voiceConsent, setVoiceConsent] = useState(false)
  const [confirmDeleteVoice, setConfirmDeleteVoice] = useState(false)
  const [confirmDeleteAccount, setConfirmDeleteAccount] = useState(false)

  const [feedback, setFeedback] = useState(null)
  const [error, setError] = useState(null)
  const isMounted = useRef(true)

  useEffect(() => {
    isMounted.current = true
    applyPreferences()
    return () => {
      isMounted.current = false
      api.stopAudio()
    }
  }, [])

  // Keep form in sync if auth user updates
  useEffect(() => {
    if (user) {
      setCaregiverName(user.caregiver_name || '')
      setCaregiverPhone(user.caregiver_phone || '')
    }
  }, [user])

  const flashFeedback = (msgKey) => {
    setFeedback(t(msgKey))
    setTimeout(() => {
      if (isMounted.current) setFeedback(null)
    }, 4000)
  }

  // --- Display and Language ---
  // The app's language belongs to this device (localStorage), never to the account.
  const handleSetLanguage = (nextLang) => {
    if (nextLang === lang) return
    setLang(nextLang)
    flashFeedback('settings.savedSuccess')
  }

  // The language the user speaks is the account's: Prisma and Timbre follow it, and recordings
  // in the old one stop counting, so it is asked first. The new language's everyday phrases are
  // added next to the old ones (docs/API.md, PATCH /me).
  const speakName = (code) => t(code === 'hi' ? 'settings.speakHindi' : 'settings.speakEnglish')
  const handleSetSpeakLanguage = async () => {
    setBusy('language')
    setError(null)
    try {
      const updated = await api.updateMe({ language: confirmSpeak })
      if (isMounted.current) signedIn(updated)
      await api.loadDefaultPhrases()
      if (isMounted.current) {
        setConfirmSpeak(null)
        flashFeedback('settings.savedSuccess')
      }
    } catch (err) {
      if (isMounted.current) setError(err)
    } finally {
      if (isMounted.current) setBusy(null)
    }
  }

  const handleToggleLargeText = () => {
    const next = !prefs.largeText
    setPreference('largeText', next)
    setPrefs((prev) => ({ ...prev, largeText: next }))
    flashFeedback('settings.savedSuccess')
  }

  const handleToggleReducedMotion = () => {
    if (prefs.systemReducedMotion) return // Cannot override OS motion reduction
    const next = !prefs.userReducedMotion
    setPreference('reducedMotion', next)
    setPrefs((prev) => ({
      ...prev,
      userReducedMotion: next,
      reducedMotion: next,
    }))
    flashFeedback('settings.savedSuccess')
  }

  const handleToggleEnhancedFocus = () => {
    const next = !prefs.enhancedFocus
    setPreference('enhancedFocus', next)
    setPrefs((prev) => ({ ...prev, enhancedFocus: next }))
    flashFeedback('settings.savedSuccess')
  }

  // --- Caregiver Settings ---
  const handleSaveCaregiver = async (e) => {
    e.preventDefault()
    setBusy('caregiver')
    setError(null)

    const cleanedPhone = caregiverPhone.replace(/[\s\-()+]/g, '')
    if (cleanedPhone && !/^[1-9]\d{7,14}$/.test(cleanedPhone)) { // as src/api.py checks it
      setError(new Error(t('error.invalid_phone')))
      setBusy(null)
      return
    }

    try {
      const updated = await api.updateMe({
        caregiver_name: caregiverName.trim() || '',
        caregiver_phone: cleanedPhone || '',
      })
      if (isMounted.current) {
        signedIn(updated)
        flashFeedback('settings.savedSuccess')
      }
    } catch (err) {
      if (isMounted.current) setError(err)
    } finally {
      if (isMounted.current) setBusy(null)
    }
  }

  // --- Voice Controls ---
  const handleToggleUseOwnVoice = async () => {
    if (!user?.has_own_voice) return
    setBusy('voice')
    setError(null)
    try {
      const updated = await api.updateMe({
        use_own_voice: !user.use_own_voice,
      })
      if (isMounted.current) {
        signedIn(updated)
        flashFeedback('settings.savedSuccess')
      }
    } catch (err) {
      if (isMounted.current) setError(err)
    } finally {
      if (isMounted.current) setBusy(null)
    }
  }

  const handleUploadVoice = async (e) => {
    e.preventDefault()
    if (!voiceFile) return setError({ kind: 'server', code: 'no_voice_file' })
    setBusy('upload')
    setError(null)
    try {
      const updated = await api.setVoice(voiceFile)
      if (isMounted.current) {
        signedIn(updated)
        setVoiceFile(null)
        setVoiceConsent(false)
        flashFeedback('settings.savedSuccess')
      }
    } catch (err) {
      // The phrase-length wording of these two (0.3 to 15 s) is wrong for a voice (5 to 30 s).
      const length = ['audio_too_short', 'audio_too_long'].includes(err.code)
      if (isMounted.current) setError(length ? { kind: 'server', code: 'voice_length' } : err)
    } finally {
      if (isMounted.current) setBusy(null)
    }
  }

  const handlePlayVoiceSample = async () => {
    if (playingSample) {
      api.stopAudio()
      setPlayingSample(false)
      return
    }

    setPlayingSample(true)
    setError(null)
    // In the language the user speaks: that is the language Timbre is asked to speak in.
    const sampleText = user?.language === 'en' ? 'Hello, I need some water.' : 'नमस्ते, मुझे पानी चाहिए।'

    try {
      await api.say(sampleText)
    } catch (err) {
      if (isMounted.current) setError(err)
    } finally {
      if (isMounted.current) setPlayingSample(false)
    }
  }

  const handleDeleteVoice = async () => {
    setBusy('voice')
    setError(null)
    try {
      const updated = await api.deleteVoice()
      if (isMounted.current) {
        signedIn(updated)
        setConfirmDeleteVoice(false)
        flashFeedback('settings.savedSuccess')
      }
    } catch (err) {
      if (isMounted.current) setError(err)
    } finally {
      if (isMounted.current) setBusy(null)
    }
  }

  // --- Account Deletion ---
  const handleDeleteAccount = async () => {
    setBusy('account')
    setError(null)
    try {
      await deleteAccount() // signs out, and /app/* then goes home
    } catch (err) {
      if (isMounted.current) {
        setError(err)
        setBusy(null)
      }
    }
  }

  const createdDate = user?.consent_given_at
    ? new Date(user.consent_given_at).toLocaleDateString(
        lang === 'hi' ? 'hi-IN' : 'en-US',
        { year: 'numeric', month: 'short', day: 'numeric' },
      )
    : null

  return (
    <section className="screen settings-screen">
      <header className="settings-header">
        <h1>{t('settings.title')}</h1>
        <p className="muted">{t('settings.subtitle')}</p>
      </header>

      {/* Notifications and Alerts */}
      <div aria-live="polite">
        {feedback && (
          <p className="notice-banner" role="status">
            {feedback}
          </p>
        )}
        <Alert error={error} />
      </div>

      {/* Section 1: Language and Display */}
      <article className="settings-card" aria-labelledby="heading-display">
        <div className="card-header">
          <Languages className="card-icon" size={20} aria-hidden="true" strokeWidth={1.5} />
          <h2 id="heading-display">{t('settings.sectionDisplay')}</h2>
        </div>

        <div className="settings-row">
          <div className="row-text">
            <strong>{t('settings.languageLabel')}</strong>
            <p className="muted">{t('settings.languageHelp')}</p>
          </div>
          <div className="segmented-control" role="radiogroup" aria-label={t('settings.languageLabel')}>
            <button
              type="button"
              role="radio"
              aria-checked={lang === 'en'}
              className={`segment-btn ${lang === 'en' ? 'active' : ''}`}
              onClick={() => handleSetLanguage('en')}
            >
              {lang === 'en' && <Check size={14} aria-hidden="true" strokeWidth={2} />}
              <span>{t('settings.langEnglish')}</span>
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={lang === 'hi'}
              className={`segment-btn ${lang === 'hi' ? 'active' : ''}`}
              onClick={() => handleSetLanguage('hi')}
            >
              {lang === 'hi' && <Check size={14} aria-hidden="true" strokeWidth={2} />}
              <span>{t('settings.langHindi')}</span>
            </button>
          </div>
        </div>

        <hr className="divider" />

        <div className="settings-row">
          <div className="row-text">
            <strong id="speak-language-label">{t('settings.speakLanguageLabel')}</strong>
            <p className="muted">{t('settings.speakLanguageHelp')}</p>
          </div>
          <div className="segmented-control" role="radiogroup" aria-labelledby="speak-language-label">
            {['hi', 'en'].map((code) => (
              <button
                key={code}
                type="button"
                role="radio"
                aria-checked={user?.language === code}
                className={`segment-btn ${user?.language === code ? 'active' : ''}`}
                onClick={() => setConfirmSpeak(code === user?.language ? null : code)}
                disabled={busy !== null}
              >
                {user?.language === code && <Check size={14} aria-hidden="true" strokeWidth={2} />}
                <span>{speakName(code)}</span>
              </button>
            ))}
          </div>
        </div>

        {confirmSpeak && (
          <div className="inline-confirm-box" role="group" aria-labelledby="speak-language-confirm">
            <p>
              <strong id="speak-language-confirm">
                {t('settings.speakLanguageConfirm', { language: speakName(confirmSpeak) })}
              </strong>
            </p>
            <p className="muted">{t('settings.speakLanguageWarning', { language: speakName(confirmSpeak) })}</p>
            <div className="actions">
              <button
                type="button"
                className="pill-outline"
                onClick={() => setConfirmSpeak(null)}
                disabled={busy === 'language'}
                autoFocus
              >
                {t('settings.cancel')}
              </button>
              <button
                type="button"
                className="pill-outline"
                onClick={handleSetSpeakLanguage}
                disabled={busy === 'language'}
              >
                {busy === 'language'
                  ? t('settings.speakLanguageSwitching')
                  : t('settings.speakLanguageYes', { language: speakName(confirmSpeak) })}
              </button>
            </div>
          </div>
        )}

        <hr className="divider" />

        <div className="settings-row">
          <div className="row-text">
            <strong>{t('settings.textSizeLabel')}</strong>
            <p className="muted">{t('settings.textSizeHelp')}</p>
          </div>
          <div className="segmented-control" role="radiogroup" aria-label={t('settings.textSizeLabel')}>
            <button
              type="button"
              role="radio"
              aria-checked={!prefs.largeText}
              className={`segment-btn ${!prefs.largeText ? 'active' : ''}`}
              onClick={handleToggleLargeText}
            >
              {!prefs.largeText && <Check size={14} aria-hidden="true" strokeWidth={2} />}
              <span>{t('settings.textSizeDefault')}</span>
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={prefs.largeText}
              className={`segment-btn ${prefs.largeText ? 'active' : ''}`}
              onClick={handleToggleLargeText}
            >
              {prefs.largeText && <Check size={14} aria-hidden="true" strokeWidth={2} />}
              <span>{t('settings.textSizeLarge')}</span>
            </button>
          </div>
        </div>

        <hr className="divider" />

        <div className="settings-row">
          <div className="row-text">
            <strong>{t('settings.motionLabel')}</strong>
            <p className="muted">{t('settings.motionHelp')}</p>
            {prefs.systemReducedMotion && (
              <p className="field-hint system-note">
                {t('settings.motionSystemNote')}
              </p>
            )}
          </div>
          <button
            type="button"
            className={`pill-outline switch-btn ${prefs.reducedMotion ? 'active' : ''}`}
            onClick={handleToggleReducedMotion}
            disabled={prefs.systemReducedMotion}
            aria-pressed={prefs.reducedMotion}
          >
            {prefs.reducedMotion ? (
              <CheckCircle2 size={16} aria-hidden="true" strokeWidth={2} />
            ) : null}
            <span>
              {t(prefs.reducedMotion ? 'settings.motionActive' : 'settings.motionOff')}
            </span>
          </button>
        </div>
      </article>

      {/* Section 2: Accessibility and Interaction */}
      <article className="settings-card" aria-labelledby="heading-accessibility">
        <div className="card-header">
          <Type className="card-icon" size={20} aria-hidden="true" strokeWidth={1.5} />
          <h2 id="heading-accessibility">{t('settings.sectionAccessibility')}</h2>
        </div>

        <div className="settings-row">
          <div className="row-text">
            <strong>{t('settings.focusLabel')}</strong>
            <p className="muted">{t('settings.focusHelp')}</p>
          </div>
          <button
            type="button"
            className={`pill-outline switch-btn ${prefs.enhancedFocus ? 'active' : ''}`}
            onClick={handleToggleEnhancedFocus}
            aria-pressed={prefs.enhancedFocus}
          >
            {prefs.enhancedFocus && (
              <CheckCircle2 size={16} aria-hidden="true" strokeWidth={2} />
            )}
            <span>{t(prefs.enhancedFocus ? 'settings.on' : 'settings.off')}</span>
          </button>
        </div>

        <hr className="divider" />

        <div className="settings-info-box">
          <strong>{t('settings.touchLabel')}</strong>
          <p className="muted">{t('settings.touchHelp')}</p>
        </div>
      </article>

      {/* Section 3: Voice and Speech Synthesis */}
      <article className="settings-card" aria-labelledby="heading-voice">
        <div className="card-header">
          <Volume2 className="card-icon" size={20} aria-hidden="true" strokeWidth={1.5} />
          <h2 id="heading-voice">{t('settings.sectionVoice')}</h2>
        </div>

        <p className="muted">{t('settings.voiceDesc')}</p>

        <div className="voice-status-box">
          <span className="status-label">{t('settings.voiceStatusLabel')}</span>
          <span className={`status-badge ${user?.has_own_voice ? 'cloned' : 'standard'}`}>
            {t(user?.has_own_voice ? 'settings.voiceRecorded' : 'settings.voiceStandard')}
          </span>
        </div>

        {user?.has_own_voice ? (
          <div className="settings-row">
            <div className="row-text">
              <strong>{t('settings.useOwnVoiceLabel')}</strong>
              <p className="muted">{t('settings.useOwnVoiceHelp')}</p>
            </div>
            <button
              type="button"
              className={`pill-outline switch-btn ${user.use_own_voice ? 'active' : ''}`}
              onClick={handleToggleUseOwnVoice}
              disabled={busy === 'voice'}
              aria-pressed={Boolean(user.use_own_voice)}
            >
              {user.use_own_voice && (
                <CheckCircle2 size={16} aria-hidden="true" strokeWidth={2} />
              )}
              <span>{t(user.use_own_voice ? 'settings.on' : 'settings.off')}</span>
            </button>
          </div>
        ) : (
          <form className="voice-enroll-hint" onSubmit={handleUploadVoice} aria-labelledby="voice-upload-title">
            <p className="muted">{t('settings.voiceNotRecordedHelp')}</p>
            <strong id="voice-upload-title">{t('settings.voiceUploadLabel')}</strong>
            <div className="field">
              <label htmlFor="voice-file">{t('settings.voiceFile')}</label>
              <input
                id="voice-file"
                type="file"
                accept="audio/*"
                aria-describedby="voice-file-hint"
                onChange={(e) => setVoiceFile(e.target.files[0] || null)}
                disabled={busy === 'upload'}
              />
              <p className="field-hint" id="voice-file-hint">
                {t('settings.voiceUploadHelp')}
              </p>
            </div>
            <label className="check">
              <input
                type="checkbox"
                checked={voiceConsent}
                onChange={(e) => setVoiceConsent(e.target.checked)}
                disabled={busy === 'upload'}
              />
              <span>{t('settings.voiceConsent')}</span>
            </label>
            <div className="actions">
              <button
                type="submit"
                className="pill-outline"
                disabled={!voiceConsent || busy !== null}
              >
                <Upload size={16} aria-hidden="true" strokeWidth={1.5} />
                <span>{t(busy === 'upload' ? 'settings.voiceUploading' : 'settings.voiceUpload')}</span>
              </button>
            </div>
          </form>
        )}

        <div className="voice-actions-row">
          <button
            type="button"
            className="pill-outline"
            onClick={handlePlayVoiceSample}
            disabled={busy !== null}
          >
            {playingSample ? (
              <Square size={16} fill="currentColor" aria-hidden="true" />
            ) : (
              <Volume2 size={16} aria-hidden="true" strokeWidth={1.5} />
            )}
            <span>
              {t(playingSample ? 'settings.testVoiceStop' : 'settings.testVoice')}
            </span>
          </button>

          {user?.has_own_voice && !confirmDeleteVoice && (
            <button
              type="button"
              className="pill-outline destructive"
              onClick={() => setConfirmDeleteVoice(true)}
              disabled={busy !== null}
            >
              <Trash2 size={16} aria-hidden="true" strokeWidth={1.5} />
              <span>{t('settings.deleteVoice')}</span>
            </button>
          )}
        </div>

        {/* Delete Voice Model Confirmation */}
        {confirmDeleteVoice && (
          <div className="inline-confirm-box danger-box">
            <p>
              <strong>{t('settings.deleteVoiceConfirm')}</strong>
            </p>
            <p className="muted">{t('settings.deleteVoiceWarning')}</p>
            <div className="actions">
              <button
                type="button"
                className="pill-outline"
                onClick={() => setConfirmDeleteVoice(false)}
                disabled={busy === 'voice'}
              >
                {t('settings.deleteVoiceNo')}
              </button>
              <button
                type="button"
                className="pill-outline destructive"
                onClick={handleDeleteVoice}
                disabled={busy === 'voice'}
              >
                <span>
                  {t(busy === 'voice' ? 'settings.deletingVoice' : 'settings.deleteVoiceYes')}
                </span>
              </button>
            </div>
          </div>
        )}
      </article>

      {/* Section 4: Caregiver and Emergency Contact */}
      <article className="settings-card" aria-labelledby="heading-caregiver">
        <div className="card-header">
          <Phone className="card-icon" size={20} aria-hidden="true" strokeWidth={1.5} />
          <h2 id="heading-caregiver">{t('settings.sectionCaregiver')}</h2>
        </div>

        <p className="muted">{t('settings.caregiverDesc')}</p>

        <form onSubmit={handleSaveCaregiver} className="caregiver-form">
          <div className="field">
            <label htmlFor="caregiver-name">{t('settings.caregiverNameLabel')}</label>
            <input
              id="caregiver-name"
              type="text"
              value={caregiverName}
              onChange={(e) => setCaregiverName(e.target.value)}
              placeholder={t('settings.caregiverNamePlaceholder')}
              disabled={busy === 'caregiver'}
            />
          </div>

          <div className="field">
            <label htmlFor="caregiver-phone">{t('settings.caregiverPhoneLabel')}</label>
            <input
              id="caregiver-phone"
              type="tel"
              value={caregiverPhone}
              onChange={(e) => setCaregiverPhone(e.target.value)}
              placeholder={t('settings.caregiverPhonePlaceholder')}
              disabled={busy === 'caregiver'}
            />
            <p className="field-hint">{t('settings.caregiverPhoneHint')}</p>
          </div>

          <div className="caregiver-actions">
            <Pill type="submit" icon={null} arrow={false} disabled={busy === 'caregiver'}>
              {t(busy === 'caregiver' ? 'settings.savingCaregiver' : 'settings.saveCaregiver')}
            </Pill>

            {user?.caregiver_phone && (
              <a
                href={`https://wa.me/${user.caregiver_phone}`}
                target="_blank"
                rel="noopener noreferrer"
                className="pill-outline external-link-btn"
              >
                <ExternalLink size={16} aria-hidden="true" strokeWidth={1.5} />
                <span>{t('settings.openWhatsApp')}</span>
              </a>
            )}
          </div>
        </form>
      </article>

      {/* Section 5: Welcome Guide */}
      <article className="settings-card" aria-labelledby="heading-guide">
        <div className="card-header">
          <BookOpen className="card-icon" size={20} aria-hidden="true" strokeWidth={1.5} />
          <h2 id="heading-guide">{t('onboarding.revisitTitle')}</h2>
        </div>
        <p className="muted">{t('onboarding.revisitDesc')}</p>
        <div className="guide-actions">
          <button
            type="button"
            className="pill-outline"
            onClick={() => go('/app/onboarding')}
          >
            <BookOpen size={16} aria-hidden="true" strokeWidth={1.5} />
            <span>{t('onboarding.revisitTitle')}</span>
          </button>
        </div>
      </article>

      {/* Section 6: Account and Privacy */}
      <article className="settings-card" aria-labelledby="heading-account">
        <div className="card-header">
          <Shield className="card-icon" size={20} aria-hidden="true" strokeWidth={1.5} />
          <h2 id="heading-account">{t('settings.sectionAccount')}</h2>
        </div>

        <div className="account-details-grid">
          <div className="detail-item">
            <span className="muted">{t('settings.accountName')}</span>
            <strong>{user?.name}</strong>
          </div>
          <div className="detail-item">
            <span className="muted">{t('settings.accountEmail')}</span>
            <strong>{user?.email}</strong>
          </div>
          {createdDate && (
            <div className="detail-item">
              <span className="muted">{t('settings.accountCreated')}</span>
              <strong>{createdDate}</strong>
            </div>
          )}
        </div>

        <p className="privacy-statement">{t('settings.privacyNote')}</p>

        {!confirmDeleteAccount ? (
          <div className="danger-zone">
            <button
              type="button"
              className="pill-outline destructive"
              onClick={() => setConfirmDeleteAccount(true)}
              disabled={busy !== null}
            >
              <Trash2 size={16} aria-hidden="true" strokeWidth={1.5} />
              <span>{t('settings.deleteAccount')}</span>
            </button>
          </div>
        ) : (
          <div className="inline-confirm-box danger-box">
            <p>
              <strong>{t('settings.deleteAccountConfirm')}</strong>
            </p>
            <p className="muted">{t('settings.deleteAccountWarning')}</p>
            <div className="actions">
              <button
                type="button"
                className="pill-outline"
                onClick={() => setConfirmDeleteAccount(false)}
                disabled={busy === 'account'}
                autoFocus
              >
                {t('settings.deleteAccountNo')}
              </button>
              <button
                type="button"
                className="pill-outline destructive"
                onClick={handleDeleteAccount}
                disabled={busy === 'account'}
              >
                <Trash2 size={16} aria-hidden="true" strokeWidth={1.5} />
                <span>
                  {t(busy === 'account' ? 'settings.deletingAccount' : 'settings.deleteAccountYes')}
                </span>
              </button>
            </div>
          </div>
        )}
      </article>
    </section>
  )
}
