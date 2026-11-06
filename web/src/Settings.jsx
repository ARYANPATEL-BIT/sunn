import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { applyPreferences, getPreferences, setPreference } from './prefs.js'
import { useTheme } from './theme.js'
import { Alert, Button, Choices, Group, Icon, PrimaryButton, Row as SwitchRow, Sheet, Toast, useGo } from './ui/index.js'

export default function Settings() {
  const { user, signedIn, deleteAccount, logout } = useAuth()
  const { lang, setLang, t } = useLang()
  const go = useGo()
  const [theme, setTheme] = useTheme()

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

  const [feedback, setFeedback] = useState(null) // a string key, worded when shown
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
    setFeedback(msgKey)
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

  // So is the theme.
  const handleSetTheme = (next) => {
    if (next === theme) return
    setTheme(next)
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
      setError({ kind: 'server', code: 'invalid_phone' }) // Alert words it from the code
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
    ? new Date(user.consent_given_at).toLocaleDateString(lang === 'hi' ? 'hi-IN' : 'en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : null
  const sheetOpen = Boolean(confirmSpeak) || confirmDeleteVoice || confirmDeleteAccount

  return (
    <section className="screen settings-screen">
      <h1 className="large-title">{t('settings.title')}</h1>

      {/* Notifications and Alerts */}
      <div aria-live="polite">
        {feedback && <Toast>{t(feedback)}</Toast>}
        {!sheetOpen && <Alert error={error} />}
      </div>

      {/* Language and display */}
      <Group bare title={t('settings.speakLanguageLabel')} titleId="speak-language-label" footer={t('settings.speakLanguageHelp')}>
        <Choices
          labelledBy="speak-language-label"
          options={['hi', 'en'].map((code) => ({ value: code, label: speakName(code) }))}
          value={user?.language}
          onChange={(code) => setConfirmSpeak(code === user?.language ? null : code)}
          disabled={busy !== null}
        />
      </Group>

      <Group bare title={t('settings.languageLabel')} titleId="app-language-label" footer={t('settings.languageHelp')}>
        <Choices
          labelledBy="app-language-label"
          options={[
            { value: 'en', label: t('settings.langEnglish'), lang: 'en' },
            { value: 'hi', label: t('settings.langHindi'), lang: 'hi' },
          ]}
          value={lang}
          onChange={handleSetLanguage}
        />
      </Group>

      <Group bare title={t('settings.themeLabel')} titleId="theme-label" footer={t('settings.themeHelp')}>
        <Choices
          labelledBy="theme-label"
          options={['light', 'dark', 'system'].map((value) => ({ value, label: t(`theme.${value}`) }))}
          value={theme}
          onChange={handleSetTheme}
        />
      </Group>

      <Group bare title={t('settings.textSizeLabel')} titleId="text-size-label" footer={t('settings.textSizeHelp')}>
        <Choices
          labelledBy="text-size-label"
          options={[
            { value: 'default', label: t('settings.textSizeDefault') },
            { value: 'large', label: t('settings.textSizeLarge') },
          ]}
          value={prefs.largeText ? 'large' : 'default'}
          onChange={(size) => (size === 'large') !== prefs.largeText && handleToggleLargeText()}
        />
      </Group>

      {/* Accessibility */}
      <Group title={t('settings.sectionAccessibility')} titleId="heading-accessibility" footer={t('settings.touchHelp')}>
        <SwitchRow
          id="motion"
          title={t('settings.motionLabel')}
          help={t('settings.motionHelp')}
          note={prefs.systemReducedMotion && t('settings.motionSystemNote')}
          on={prefs.reducedMotion}
          onClick={handleToggleReducedMotion}
          disabled={prefs.systemReducedMotion}
        />
        <SwitchRow
          id="focus"
          title={t('settings.focusLabel')}
          help={t('settings.focusHelp')}
          on={prefs.enhancedFocus}
          onClick={handleToggleEnhancedFocus}
        />
      </Group>

      {/* Voice */}
      <Group title={t('settings.sectionVoice')} titleId="heading-voice" footer={t('settings.voiceDesc')}>
        <div className="row">
          <span className="row-text">
            <span className="row-title">{t('settings.voiceStatusLabel')}</span>
            <span className="row-sub">{t(user?.has_own_voice ? 'settings.voiceRecorded' : 'settings.voiceStandard')}</span>
          </span>
        </div>
        {user?.has_own_voice && (
          <SwitchRow
            id="own-voice"
            title={t('settings.useOwnVoiceLabel')}
            help={t('settings.useOwnVoiceHelp')}
            on={user.use_own_voice}
            onClick={handleToggleUseOwnVoice}
            disabled={busy === 'voice'}
          />
        )}
        <button type="button" className="row" onClick={handlePlayVoiceSample} disabled={busy !== null}>
          <Icon name={playingSample ? 'stop' : 'volume'} className="row-icon" />
          <span className="row-title">{t(playingSample ? 'settings.testVoiceStop' : 'settings.testVoice')}</span>
        </button>
        {user?.has_own_voice && (
          <button
            type="button"
            className="row"
            onClick={() => setConfirmDeleteVoice(true)}
            disabled={busy !== null}
            aria-haspopup="dialog"
          >
            <Icon name="trash" className="row-icon" />
            <span className="row-title">{t('settings.deleteVoice')}</span>
          </button>
        )}
      </Group>

      {!user?.has_own_voice && (
        <form className="group-wrap" onSubmit={handleUploadVoice} aria-labelledby="voice-upload-title">
          <h2 className="group-title" id="voice-upload-title">
            {t('settings.voiceUploadLabel')}
          </h2>
          <div className="group">
            <p className="row row-note">{t('settings.voiceNotRecordedHelp')}</p>
            <div className="row file-row">
              <label htmlFor="voice-file" className="row-title">
                {t('settings.voiceFile')}
              </label>
              {/* The browser's own picker says "Choose file" in the browser's language; this button
                  says it in the app's. The input stays focusable, and its ring shows on the button. */}
              <input
                id="voice-file"
                type="file"
                accept="audio/*"
                className="visually-hidden"
                aria-describedby="voice-file-hint"
                onChange={(e) => setVoiceFile(e.target.files[0] || null)}
                disabled={busy === 'upload'}
              />
              <label htmlFor="voice-file" className="button small file-pick" aria-hidden="true">
                <Icon name="fileAudio" />
                <span>{voiceFile ? voiceFile.name : t('settings.voiceChoose')}</span>
              </label>
            </div>
            <label className="row check-row">
              <input
                type="checkbox"
                checked={voiceConsent}
                onChange={(e) => setVoiceConsent(e.target.checked)}
                disabled={busy === 'upload'}
              />
              <span className="row-title">{t('settings.voiceConsent')}</span>
            </label>
          </div>
          <p className="group-footer" id="voice-file-hint">
            {t('settings.voiceUploadHelp')}
          </p>
          <div className="actions">
            <Button type="submit" icon="upload" disabled={!voiceConsent || busy !== null}>
              {t(busy === 'upload' ? 'settings.voiceUploading' : 'settings.voiceUpload')}
            </Button>
          </div>
        </form>
      )}

      {/* Caregiver and emergency contact */}
      <form className="group-wrap" onSubmit={handleSaveCaregiver} aria-labelledby="heading-caregiver">
        <h2 className="group-title" id="heading-caregiver">
          {t('settings.sectionCaregiver')}
        </h2>
        <div className="fields plate">
          <div className="field-cell">
            <label htmlFor="caregiver-name" className="field-label">
              {t('settings.caregiverNameLabel')}
            </label>
            <input
              id="caregiver-name"
              type="text"
              value={caregiverName}
              onChange={(e) => setCaregiverName(e.target.value)}
              placeholder={t('settings.caregiverNamePlaceholder')}
              disabled={busy === 'caregiver'}
            />
          </div>
          <div className="field-cell">
            <label htmlFor="caregiver-phone" className="field-label">
              {t('settings.caregiverPhoneLabel')}
            </label>
            <input
              id="caregiver-phone"
              type="tel"
              value={caregiverPhone}
              onChange={(e) => setCaregiverPhone(e.target.value)}
              placeholder={t('settings.caregiverPhonePlaceholder')}
              aria-describedby="caregiver-phone-hint"
              disabled={busy === 'caregiver'}
            />
          </div>
        </div>
        <p className="group-footer" id="caregiver-phone-hint">
          {t('settings.caregiverDesc')} {t('settings.caregiverPhoneHint')}
        </p>
        <div className="actions">
          <Button type="submit" disabled={busy === 'caregiver'}>
            {t(busy === 'caregiver' ? 'settings.savingCaregiver' : 'settings.saveCaregiver')}
          </Button>
          {user?.caregiver_phone && (
            <a href={`https://wa.me/${user.caregiver_phone}`} target="_blank" rel="noopener noreferrer" className="button">
              <Icon name="externalLink" />
              <span>{t('settings.openWhatsApp')}</span>
            </a>
          )}
        </div>
      </form>

      {/* Welcome guide */}
      <Group>
        <button type="button" className="row" onClick={() => go('/app/onboarding')}>
          <Icon name="book" className="row-icon" />
          <span className="row-text">
            <span className="row-title">{t('onboarding.revisitTitle')}</span>
            <span className="row-sub">{t('onboarding.revisitDesc')}</span>
          </span>
          <Icon name="chevronRight" className="row-chevron" />
        </button>
      </Group>

      {/* Account and privacy */}
      <Group title={t('settings.sectionAccount')} titleId="heading-account" footer={t('settings.privacyNote')}>
        <div className="row">
          <span className="row-title">{t('settings.accountName')}</span>
          <span className="row-value">{user?.name}</span>
        </div>
        <div className="row">
          <span className="row-title">{t('settings.accountEmail')}</span>
          <span className="row-value">{user?.email}</span>
        </div>
        {createdDate && (
          <div className="row">
            <span className="row-title">{t('settings.accountCreated')}</span>
            <span className="row-value">{createdDate}</span>
          </div>
        )}
      </Group>

      <Group>
        <button type="button" className="row" onClick={logout}>
          <Icon name="logOut" className="row-icon" />
          <span className="row-title">{t('app.logOut')}</span>
        </button>
        <button
          type="button"
          className="row"
          onClick={() => setConfirmDeleteAccount(true)}
          disabled={busy !== null}
          aria-haspopup="dialog"
        >
          <Icon name="trash" className="row-icon" />
          <span className="row-title">{t('settings.deleteAccount')}</span>
        </button>
      </Group>

      {/* Asked first: the language spoken, deleting the voice, deleting the account */}
      <Sheet open={Boolean(confirmSpeak)} onClose={() => setConfirmSpeak(null)} labelledBy="speak-language-confirm">
        <div className="confirm">
          <h2 className="sheet-title" id="speak-language-confirm">
            {t('settings.speakLanguageConfirm', { language: speakName(confirmSpeak) })}
          </h2>
          <p className="sheet-text">{t('settings.speakLanguageWarning', { language: speakName(confirmSpeak) })}</p>
          <Alert error={error} />
          <div className="actions stacked">
            <PrimaryButton onClick={handleSetSpeakLanguage} disabled={busy === 'language'}>
              {busy === 'language'
                ? t('settings.speakLanguageSwitching')
                : t('settings.speakLanguageYes', { language: speakName(confirmSpeak) })}
            </PrimaryButton>
            <button
              type="button"
              className="button"
              onClick={() => setConfirmSpeak(null)}
              disabled={busy === 'language'}
              data-autofocus
            >
              {t('settings.cancel')}
            </button>
          </div>
        </div>
      </Sheet>

      <Sheet open={confirmDeleteVoice} onClose={() => setConfirmDeleteVoice(false)} labelledBy="delete-voice-confirm">
        <div className="confirm">
          <h2 className="sheet-title" id="delete-voice-confirm">
            {t('settings.deleteVoiceConfirm')}
          </h2>
          <p className="sheet-text">{t('settings.deleteVoiceWarning')}</p>
          <Alert error={error} />
          <div className="actions stacked">
            <button
              type="button"
              className="button"
              onClick={() => setConfirmDeleteVoice(false)}
              disabled={busy === 'voice'}
              data-autofocus
            >
              {t('settings.deleteVoiceNo')}
            </button>
            <button type="button" className="button" onClick={handleDeleteVoice} disabled={busy === 'voice'}>
              <Icon name="trash" />
              <span>{t(busy === 'voice' ? 'settings.deletingVoice' : 'settings.deleteVoiceYes')}</span>
            </button>
          </div>
        </div>
      </Sheet>

      <Sheet open={confirmDeleteAccount} onClose={() => setConfirmDeleteAccount(false)} labelledBy="delete-account-confirm">
        <div className="confirm">
          <h2 className="sheet-title" id="delete-account-confirm">
            {t('settings.deleteAccountConfirm')}
          </h2>
          <p className="sheet-text">{t('settings.deleteAccountWarning')}</p>
          <Alert error={error} />
          <div className="actions stacked">
            <button
              type="button"
              className="button"
              onClick={() => setConfirmDeleteAccount(false)}
              disabled={busy === 'account'}
              data-autofocus
            >
              {t('settings.deleteAccountNo')}
            </button>
            <button type="button" className="button" onClick={handleDeleteAccount} disabled={busy === 'account'}>
              <Icon name="trash" />
              <span>{t(busy === 'account' ? 'settings.deletingAccount' : 'settings.deleteAccountYes')}</span>
            </button>
          </div>
        </div>
      </Sheet>
    </section>
  )
}
