import { Check, CircleAlert, Eye, EyeOff } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router-dom'
import * as api from './api.js'
import { safeNext, useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { isOnboarded } from './prefs.js'
import { Alert, errorText, ICON, LangToggle, Pill, reducedMotion, ThemeToggle, useGo, Wordmark } from './ui.jsx'

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

// One cell of a grouped form: the label above the input, then a hint or this field's error.
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
          <CircleAlert {...ICON} />
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
    <>
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
        {shown ? <EyeOff {...ICON} /> : <Eye {...ICON} />}
        <span aria-hidden="true">{t(shown ? 'auth.hide' : 'auth.show')}</span>
      </button>
    </>
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

// The shared frame: the wordmark, language and theme at the top, then one centered column.
function AuthFrame({ title, children }) {
  return (
    <div className="auth">
      <header className="bar">
        <Wordmark />
        <div className="bar-end">
          <LangToggle />
          <ThemeToggle />
        </div>
      </header>
      <main className="auth-column">
        <h1 className="large-title">{title}</h1>
        {children}
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

export function LoginPage() {
  const { t } = useLang()
  const { status, user, signedIn } = useAuth()
  const [params] = useSearchParams()
  const go = useGo()
  const next = safeNext(params.get('next'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const refs = { email: useRef(null), password: useRef(null) }
  const { errors, show } = useFormErrors(refs)
  const leaving = useRef(false)

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
    <AuthFrame title={t('login.title')}>
      <form className="auth-form" onSubmit={submit} noValidate>
        <div className="group">
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
        <Pill type="submit" className="block" disabled={busy}>
          {t(busy ? 'login.busy' : 'login.submit')}
        </Pill>
      </form>
      <p className="auth-switch">
        {t('login.new')}{' '}
        <Link to={signupLink} viewTransition={!reducedMotion()}>
          {t('login.create')}
        </Link>
      </p>
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
  const refs = { name: useRef(null), email: useRef(null), password: useRef(null), invite_code: useRef(null) }
  const { errors, show, fromApi } = useFormErrors(refs)
  const leaving = useRef(false)

  useEffect(() => {
    let active = true
    api
      .config()
      .then((cfg) => {
        if (active && cfg?.invite_required) {
          setInviteRequired(true)
        }
      })
      .catch(() => {})
    return () => {
      active = false
    }
  }, [])

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
    <AuthFrame title={t('signup.title')}>
      <form className="auth-form" onSubmit={submit} noValidate>
        <div className="group">
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
                <Check className="choice-check" {...ICON} />
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
        <Pill
          type="submit"
          className="block"
          disabled={!consent || busy}
          aria-describedby={consent ? undefined : 'consent-needed'}
        >
          {t(busy ? 'signup.busy' : 'signup.submit')}
        </Pill>
        {!consent && (
          <p className="form-hint" id="consent-needed">
            {t('signup.consentNeeded')}
          </p>
        )}
      </form>
      <p className="auth-switch">
        {t('signup.have')}{' '}
        <Link to={loginLink} viewTransition={!reducedMotion()}>
          {t('signup.signIn')}
        </Link>
      </p>
    </AuthFrame>
  )
}
