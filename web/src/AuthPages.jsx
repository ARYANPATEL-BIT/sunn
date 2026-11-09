import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import * as api from './api.js'
import { safeNext, useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { isOnboarded } from './prefs.js'
import { Alert, errorText, Grille, Icon, LangToggle, PrimaryButton, reducedMotion, ThemeToggle, useGo, Wordmark } from './ui/index.js'

const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const MIN_PASSWORD = 8
// Which field a refusal from the API is about, so its message sits under that field.
const FIELD_OF = {
  no_name: 'name',
  bad_email: 'email',
  email_taken: 'email',
  short_password: 'password',
  invite_required: 'invite_code',
  no_invite_code: 'invite_code',
}

// One field: the label above the input, then a hint and, under it, this field's error with an icon.
function Field({ id, label, hint, error, children }) {
  const i18n = useLang()
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined
  return (
    <div className={`field-cell ${error ? 'invalid' : ''}`}>
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      {children({ id, 'aria-describedby': describedBy, 'aria-invalid': error ? true : undefined })}
      {hint && (
        <p className="field-hint" id={`${id}-hint`}>
          {hint}
        </p>
      )}
      {error && (
        <p className="field-error" id={`${id}-error`}>
          <Icon name="alert" />
          <span>{errorText(i18n, error)}</span>
        </p>
      )}
    </div>
  )
}

function PasswordInput({ value, onChange, inputRef, autoComplete, ...aria }) {
  const { t } = useLang()
  const [shown, setShown] = useState(false)
  return (
    <div className="input-with-action">
      <input
        ref={inputRef}
        type={shown ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        autoCapitalize="none"
        spellCheck={false}
        {...aria}
      />
      <button
        type="button"
        className="reveal"
        aria-controls={aria.id}
        aria-label={t(shown ? 'auth.hideLabel' : 'auth.showLabel')}
        onClick={() => setShown(!shown)}
      >
        <Icon name={shown ? 'eyeOff' : 'eye'} />
        <span aria-hidden="true">{t(shown ? 'auth.hide' : 'auth.show')}</span>
      </button>
    </div>
  )
}

function EmailInput({ value, onChange, inputRef, ...aria }) {
  return (
    <input
      ref={inputRef}
      type="email"
      inputMode="email"
      autoComplete="email"
      autoCapitalize="none"
      spellCheck={false}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      {...aria}
    />
  )
}

// The shared frame: the wordmark, language and theme at the top, then a small device panel.
function AuthFrame({ title, children, footer }) {
  return (
    <div className="auth">
      <header className="site-nav">
        <div className="bar">
          <Wordmark />
          <div className="bar-end">
            <LangToggle />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="auth-main">
        <div className="device device-object auth-panel">
          <Grille className="grille-strip" />
          <h1 className="large-title">{title}</h1>
          {children}
        </div>
        {footer}
      </main>
    </div>
  )
}

// form-level errors go in an alert; field errors under their field, and that field gets focus.
function useFormErrors(refs) {
  const [errors, setErrors] = useState({})
  function show(found) {
    setErrors(found)
    const first = Object.keys(refs).find((name) => found[name])
    if (first) refs[first].current?.focus()
  }
  function fromApi(error) {
    show(FIELD_OF[error.code] ? { [FIELD_OF[error.code]]: error } : { form: error })
  }
  return { errors, show, fromApi }
}

const refusal = (code) => ({ kind: 'server', code })

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" style={{ display: 'block', flexShrink: 0 }}>
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.16 0 9.98 0 12s.45 3.84 1.25 5.42l4.03-3.15Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98Z"
      />
    </svg>
  )
}

function useGoogleSignIn({ clientId, buttonRef, text = 'signin_with', onToken, onError }) {
  const callbackRef = useRef(onToken)
  callbackRef.current = onToken
  const errorRef = useRef(onError)
  errorRef.current = onError

  useEffect(() => {
    if (!clientId || !buttonRef.current) return
    let active = true

    function renderGsi() {
      if (!active || !window.google?.accounts?.id || !buttonRef.current) return
      try {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (res) => {
            if (res?.credential) {
              callbackRef.current(res.credential)
            } else {
              errorRef.current?.(refusal('invalid_google_token'))
            }
          },
        })
        const availableWidth = buttonRef.current ? buttonRef.current.offsetWidth : 280
        const buttonWidth = Math.min(280, Math.max(200, availableWidth || 280))
        buttonRef.current.innerHTML = ''
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: 'outline',
          size: 'large',
          type: 'standard',
          shape: 'rectangular',
          text,
          width: buttonWidth,
        })
      } catch (err) {
        console.error('Failed to initialize Google Sign-In', err)
      }
    }

    if (window.google?.accounts?.id) {
      renderGsi()
    } else {
      const existing = document.getElementById('google-gsi-client')
      if (!existing) {
        const script = document.createElement('script')
        script.id = 'google-gsi-client'
        script.src = 'https://accounts.google.com/gsi/client'
        script.async = true
        script.defer = true
        script.onload = () => {
          if (active) renderGsi()
        }
        document.head.appendChild(script)
      } else {
        existing.addEventListener('load', renderGsi)
      }
    }

    return () => {
      active = false
    }
  }, [clientId, buttonRef, text])
}

export function LoginPage() {
  const { t } = useLang()
  const { status, user, signedIn } = useAuth()
  const [params] = useSearchParams()
  const go = useGo()
  const next = safeNext(params.get('next'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [googleClientId, setGoogleClientId] = useState('')
  const refs = { email: useRef(null), password: useRef(null) }
  const googleBtnRef = useRef(null)
  const { errors, show } = useFormErrors(refs)
  const leaving = useRef(false)

  useEffect(() => {
    let active = true
    api
      .googleConfig()
      .then((cfg) => {
        if (active && cfg?.client_id) {
          setGoogleClientId(cfg.client_id)
        }
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [])

  useGoogleSignIn({
    clientId: googleClientId,
    buttonRef: googleBtnRef,
    text: 'signin_with',
    onToken: async (credential) => {
      setBusy(true)
      show({})
      try {
        const me = await api.authGoogle({ id_token: credential })
        leaving.current = true
        signedIn(me)
        const target = next || (isOnboarded(me.id) ? '/app/speak' : '/app/onboarding')
        go(target, { replace: true })
      } catch (error) {
        show({ form: error })
        setBusy(false)
      }
    },
    onError: (err) => show({ form: err }),
  })

  // Already signed in (e.g. the back button): straight on.
  if (status === 'ready' && user && !leaving.current) {
    const target = next || (isOnboarded(user.id) ? '/app/speak' : '/app/onboarding')
    return <Navigate replace to={target} />
  }

  async function submit(e) {
    e.preventDefault()
    const found = {}
    if (!EMAIL.test(email.trim())) found.email = refusal('bad_email')
    if (!password) found.password = refusal('no_password')
    if (Object.keys(found).length) return show(found)
    setBusy(true)
    show({})
    try {
      const me = await api.login(email.trim(), password)
      leaving.current = true
      signedIn(me)
      const target = next || (isOnboarded(me.id) ? '/app/speak' : '/app/onboarding')
      go(target, { replace: true })
    } catch (error) {
      // A wrong email and a wrong password get the same answer, so it isn't put under either.
      show({ form: error })
      setBusy(false)
    }
  }

  const signupLink = next ? `/signup?next=${encodeURIComponent(next)}` : '/signup'
  return (
    <AuthFrame
      title={t('login.title')}
      footer={
        <p className="auth-switch">
          {t('login.new')}{' '}
          <Link to={signupLink} viewTransition={!reducedMotion()}>
            {t('login.create')}
          </Link>
        </p>
      }
    >
      <form className="auth-form" onSubmit={submit} noValidate>
        <div className="fields">
          <Field id="login-email" label={t('auth.email')} error={errors.email}>
            {(aria) => <EmailInput value={email} onChange={setEmail} inputRef={refs.email} {...aria} />}
          </Field>
          <Field id="login-password" label={t('auth.password')} error={errors.password}>
            {(aria) => (
              <PasswordInput
                value={password}
                onChange={setPassword}
                inputRef={refs.password}
                autoComplete="current-password"
                {...aria}
              />
            )}
          </Field>
        </div>
        <Alert error={errors.form} />
        <PrimaryButton type="submit" className="block" disabled={busy}>
          {t(busy ? 'login.busy' : 'login.submit')}
        </PrimaryButton>
        <div className="oauth-section">
          <div className="oauth-divider" role="separator">
            <span>{t('auth.orDivider')}</span>
          </div>
          {googleClientId ? (
            <div ref={googleBtnRef} className="google-btn-wrapper" />
          ) : (
            <button
              type="button"
              className="google-btn-custom"
              onClick={() => show({ form: refusal('google_not_configured') })}
            >
              <GoogleIcon />
              <span>{t('auth.googleButton')}</span>
            </button>
          )}
        </div>
      </form>
    </AuthFrame>
  )
}

export function SignupPage() {
  const { t, lang } = useLang()
  const { status, user, signedIn } = useAuth()
  const [params] = useSearchParams()
  const go = useGo()
  const next = safeNext(params.get('next'))
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [inviteCode, setInviteCode] = useState(params.get('invite') || '')
  const [inviteRequired, setInviteRequired] = useState(false)
  const [speaks, setSpeaks] = useState(lang) // the language the person speaks, not the page's
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [googleClientId, setGoogleClientId] = useState('')
  const refs = { name: useRef(null), email: useRef(null), password: useRef(null), invite_code: useRef(null) }
  const googleBtnRef = useRef(null)
  const { errors, show, fromApi } = useFormErrors(refs)
  const leaving = useRef(false)
  const signupStateRef = useRef({ inviteRequired, inviteCode, speaks, consent })
  signupStateRef.current = { inviteRequired, inviteCode, speaks, consent }

  useEffect(() => {
    let active = true
    api
      .config()
      .then((cfg) => {
        if (!active) return
        if (cfg?.invite_required) {
          setInviteRequired(true)
        }
      })
      .catch(() => {})
    api
      .googleConfig()
      .then((cfg) => {
        if (!active) return
        if (cfg?.client_id) {
          setGoogleClientId(cfg.client_id)
        }
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [])

  useGoogleSignIn({
    clientId: googleClientId,
    buttonRef: googleBtnRef,
    text: 'signup_with',
    onToken: async (credential) => {
      const state = signupStateRef.current
      if (state.inviteRequired && !state.inviteCode.trim()) {
        return show({ invite_code: refusal('no_invite_code') })
      }
      if (!state.consent) {
        return show({ form: refusal('consent_required') })
      }
      setBusy(true)
      show({})
      let me
      try {
        me = await api.authGoogle({
          id_token: credential,
          invite_code: state.inviteCode.trim() || undefined,
          language: state.speaks,
          consent: true,
        })
      } catch (error) {
        fromApi(error)
        return setBusy(false)
      }
      const phrasesFailed = await api.loadDefaultPhrases().then(
        () => false,
        () => true,
      )
      leaving.current = true
      signedIn(me)
      go('/app/onboarding', { replace: true, state: { phrasesFailed } })
    },
    onError: (err) => show({ form: err }),
  })

  if (status === 'ready' && user && !leaving.current) return <Navigate replace to={next || '/app/speak'} />

  async function submit(e) {
    e.preventDefault()
    if (!consent) return
    const found = {}
    if (!name.trim()) found.name = refusal('no_name')
    if (!EMAIL.test(email.trim())) found.email = refusal('bad_email')
    if (inviteRequired && !inviteCode.trim()) found.invite_code = refusal('no_invite_code')
    if (password.length < MIN_PASSWORD) found.password = refusal('short_password')
    if (Object.keys(found).length) return show(found)
    setBusy(true)
    show({})
    let me
    try {
      me = await api.signup({
        name: name.trim(),
        email: email.trim(),
        password,
        language: speaks,
        invite_code: inviteCode.trim() || undefined,
      })
    } catch (error) {
      fromApi(error)
      return setBusy(false)
    }
    // The account exists now. If the phrases don't load, enroll offers to add them again.
    const phrasesFailed = await api.loadDefaultPhrases().then(
      () => false,
      () => true,
    )
    leaving.current = true
    signedIn(me)
    go('/app/onboarding', { replace: true, state: { phrasesFailed } })
  }

  const loginLink = next ? `/login?next=${encodeURIComponent(next)}` : '/login'
  return (
    <AuthFrame
      title={t('signup.title')}
      footer={
        <p className="auth-switch">
          {t('signup.have')}{' '}
          <Link to={loginLink} viewTransition={!reducedMotion()}>
            {t('signup.signIn')}
          </Link>
        </p>
      }
    >
      <form className="auth-form" onSubmit={submit} noValidate>
        <div className="fields">
          <Field id="signup-name" label={t('signup.name')} error={errors.name}>
            {(aria) => (
              <input
                ref={refs.name}
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                autoCapitalize="words"
                {...aria}
              />
            )}
          </Field>
          <Field id="signup-email" label={t('auth.email')} error={errors.email}>
            {(aria) => <EmailInput value={email} onChange={setEmail} inputRef={refs.email} {...aria} />}
          </Field>
          {inviteRequired && (
            <Field
              id="signup-invite"
              label={t('signup.inviteCode')}
              hint={t('signup.inviteHint')}
              error={errors.invite_code}
            >
              {(aria) => (
                <input
                  ref={refs.invite_code}
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  autoComplete="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  placeholder={t('signup.invitePlaceholder')}
                  {...aria}
                />
              )}
            </Field>
          )}
          <Field
            id="signup-password"
            label={t('auth.password')}
            hint={t('signup.passwordHint')}
            error={errors.password}
          >
            {(aria) => (
              <PasswordInput
                value={password}
                onChange={setPassword}
                inputRef={refs.password}
                autoComplete="new-password"
                {...aria}
              />
            )}
          </Field>
        </div>

        <fieldset className="group-wrap">
          <legend className="group-title">{t('signup.language')}</legend>
          <div className="group">
            {[
              ['hi', 'हिंदी'],
              ['en', 'English'],
            ].map(([code, label]) => (
              <label key={code} className="row choice" lang={code}>
                <input
                  type="radio"
                  name="speaks"
                  value={code}
                  className="visually-hidden"
                  checked={speaks === code}
                  onChange={() => setSpeaks(code)}
                />
                <span className="row-title">{label}</span>
                <Icon name="check" className="choice-check" />
              </label>
            ))}
          </div>
          <p className="group-footer">{t('signup.languageHint')}</p>
        </fieldset>

        <fieldset className="group-wrap">
          <legend className="group-title">{t('signup.consentTitle')}</legend>
          <div className="group">
            <p className="row consent-body" id="consent-body">
              {t('signup.consentBody')}
            </p>
            <label className="row check-row">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                aria-describedby="consent-body"
              />
              <span className="row-title">{t('signup.consent')}</span>
            </label>
          </div>
        </fieldset>

        <Alert error={errors.form} />
        <PrimaryButton
          type="submit"
          className="block"
          disabled={!consent || busy}
          aria-describedby={consent ? undefined : 'consent-needed'}
        >
          {t(busy ? 'signup.busy' : 'signup.submit')}
        </PrimaryButton>
        {!consent && (
          <p className="form-hint" id="consent-needed">
            {t('signup.consentNeeded')}
          </p>
        )}
        <div className="oauth-section">
          <div className="oauth-divider" role="separator">
            <span>{t('auth.orDivider')}</span>
          </div>
          {googleClientId ? (
            <div ref={googleBtnRef} className="google-btn-wrapper" />
          ) : (
            <button
              type="button"
              className="google-btn-custom"
              onClick={() => {
                if (!consent) {
                  return show({ form: refusal('consent_required') })
                }
                show({ form: refusal('google_not_configured') })
              }}
            >
              <GoogleIcon />
              <span>{t('auth.googleButton')}</span>
            </button>
          )}
        </div>
      </form>
    </AuthFrame>
  )
}
