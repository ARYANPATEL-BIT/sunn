import { Check, CheckCircle2, CircleAlert, Contrast, Moon, Sun, X } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useLang } from './i18n/index.jsx'
import { nextTheme, useTheme } from './theme.js'

export const ICON = { 'aria-hidden': true, strokeWidth: 1.5 }

export const reducedMotion = () =>
  matchMedia('(prefers-reduced-motion: reduce)').matches ||
  (typeof document !== 'undefined' && document.documentElement.classList.contains('reduced-motion'))

// navigate(), with a quick crossfade where the view transitions api exists (not with reduced motion).
export function useGo() {
  const navigate = useNavigate()
  return (to, options) => navigate(to, { viewTransition: !reducedMotion(), ...options })
}

// The "Sunn" wordmark, linking home. Always Latin: it is the name, in both languages.
export function Wordmark() {
  const { t } = useLang()
  return (
    <Link to="/" className="wordmark" lang="en" aria-label={t('nav.home')} viewTransition={!reducedMotion()}>
      Sunn
    </Link>
  )
}

export const failure = (kind) => Object.assign(new Error(kind), { kind })

// What happened and what to do, in the current language. A refusal the API explains with a
// code (bad_login, email_taken…) gets its own words; anything else is worded by its kind.
export function errorText({ t, has }, error) {
  if (error.code && has(`error.${error.code}`)) {
    return t(`error.${error.code}`, { minutes: Math.max(1, Math.ceil((error.retryAfter || 0) / 60)) })
  }
  return t(has(`error.${error.kind}`) ? `error.${error.kind}` : 'error.server')
}

export function Alert({ error, id }) {
  const i18n = useLang()
  if (!error) return null
  return (
    <p className="alert" role="alert" id={id}>
      <CircleAlert className="alert-icon" {...ICON} />
      <span>{errorText(i18n, error)}</span>
    </p>
  )
}

// A short confirmation that something was saved, above the tab bar for a few seconds.
export function Toast({ children }) {
  return (
    <p className="toast" role="status">
      <CheckCircle2 className="toast-icon" {...ICON} />
      <span>{children}</span>
    </p>
  )
}

// EN / हिं. Switches the whole interface; the user's own phrases stay as stored.
export function LangToggle() {
  const { lang, setLang, t } = useLang()
  return (
    <div className="lang-toggle" role="group" aria-label={t('lang.label')}>
      <button type="button" lang="en" aria-pressed={lang === 'en'} onClick={() => setLang('en')}>
        EN
      </button>
      <button type="button" lang="hi" aria-pressed={lang === 'hi'} onClick={() => setLang('hi')}>
        हिं
      </button>
    </div>
  )
}

// Automatic is the half-filled circle, as on Apple's own appearance settings.
const THEME_ICON = { light: Sun, dark: Moon, system: Contrast }

// Steps through automatic, dark and light; Settings has all three as a list.
export function ThemeToggle() {
  const { t } = useLang()
  const [theme, setTheme] = useTheme()
  const Icon = THEME_ICON[theme]
  return (
    <button
      type="button"
      className="icon-button"
      onClick={() => setTheme(nextTheme(theme))}
      aria-label={t('theme.toggle', { theme: t(`theme.${theme}`) })}
      title={t('theme.toggle', { theme: t(`theme.${theme}`) })}
    >
      <Icon {...ICON} />
    </button>
  )
}

// The primary action: black in light, white in dark, fully round. At most one per screen.
export function Pill({ children, icon: Icon, className = '', ...props }) {
  return (
    <button type="button" className={`pill ${className}`} {...props}>
      {Icon && <Icon className="pill-icon" {...ICON} />}
      <span>{children}</span>
    </button>
  )
}

// iOS switch. Its name comes from the row it sits in (labelledBy).
export function Switch({ on, labelledBy, describedBy, ...props }) {
  return (
    <button
      type="button"
      className="switch"
      aria-pressed={Boolean(on)}
      aria-labelledby={labelledBy}
      aria-describedby={describedBy}
      {...props}
    />
  )
}

// A grouped list: a title above, the rows in one rounded block, a footnote below. With bare,
// the children bring their own block (a radiogroup of Choices, a form).
export function Group({ title, titleId, footer, footerId, bare, children }) {
  return (
    <div className="group-wrap">
      {title && (
        <h2 className="group-title" id={titleId}>
          {title}
        </h2>
      )}
      {bare ? children : <div className="group">{children}</div>}
      {footer && (
        <p className="group-footer" id={footerId}>
          {footer}
        </p>
      )}
    </div>
  )
}

// One choice of a few, as rows with a checkmark (iOS Settings). A radiogroup of radios.
export function Choices({ label, labelledBy, options, value, onChange, disabled }) {
  return (
    <div className="group" role="radiogroup" aria-label={label} aria-labelledby={labelledBy}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          className="row choice"
          onClick={() => onChange(option.value)}
          disabled={disabled}
        >
          <span className="row-title" lang={option.lang}>
            {option.label}
          </span>
          <Check className="choice-check" {...ICON} />
        </button>
      ))}
    </div>
  )
}

// Chips: one of a few, in a row that scrolls sideways when it doesn't fit.
export function Chips({ label, options, value, onChange, disabled }) {
  return (
    <div className="chips" role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          className="chip"
          onClick={() => onChange(option.value)}
          disabled={disabled}
        >
          {option.dot && <span className="dot-red" aria-hidden="true" />}
          {option.label}
        </button>
      ))}
    </div>
  )
}

// A bottom sheet: a modal <dialog>, so focus stays inside, Escape closes it and the page
// behind is inert. Mount it with open; it slides out before it unmounts. The element with
// data-autofocus (or the first control) gets focus; focus goes back where it was afterwards.
// Sheets without their own Cancel get a close button (closable).
export function Sheet({ open, onClose, label, labelledBy, closable, className = '', children }) {
  const { t } = useLang()
  const dialog = useRef(null)
  const shown = useRef(children)
  const [mounted, setMounted] = useState(open)
  const [closing, setClosing] = useState(false)
  if (open) shown.current = children
  if (open && !mounted) setMounted(true)
  if (open && closing) setClosing(false)

  useEffect(() => {
    if (open || !mounted) return
    if (reducedMotion()) return setMounted(false)
    setClosing(true)
    const fallback = setTimeout(() => setMounted(false), 400) // if animationend never comes
    return () => clearTimeout(fallback)
  }, [open, mounted])

  useLayoutEffect(() => {
    if (!mounted) return
    const el = dialog.current
    const before = document.activeElement
    el.showModal()
    ;(el.querySelector('[data-autofocus]') || el.querySelector('input, textarea, button:not(.sheet-close)'))?.focus()
    return () => {
      el.close()
      if (before?.isConnected) before.focus({ preventScroll: true })
    }
  }, [mounted])

  if (!mounted) return null
  return (
    <dialog
      ref={dialog}
      className={`sheet ${closing ? 'is-closing' : ''} ${className}`}
      aria-label={label}
      aria-labelledby={labelledBy}
      inert={closing || undefined}
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      onAnimationEnd={(e) => e.target === e.currentTarget && closing && setMounted(false)}
    >
      <div className="sheet-body">
        {closable && (
          <button type="button" className="sheet-close icon-button" onClick={onClose} aria-label={t('sheet.close')}>
            <X {...ICON} />
          </button>
        )}
        {open ? children : shown.current}
      </div>
    </dialog>
  )
}
