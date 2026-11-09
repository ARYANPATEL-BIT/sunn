import { Link, useNavigate } from 'react-router-dom'
import { useLang } from '../i18n/index.jsx'
import { nextTheme, resolveTheme, useTheme } from '../theme.js'
import { Icon } from './icons.jsx'

export const reducedMotion = () =>
  matchMedia('(prefers-reduced-motion: reduce)').matches ||
  (typeof document !== 'undefined' && document.documentElement.classList.contains('reduced-motion'))

// navigate(), with a quick crossfade where the view transitions api exists (not with reduced motion).
export function useGo() {
  const navigate = useNavigate()
  return (to, options) => navigate(to, { viewTransition: !reducedMotion(), ...options })
}

// "Sunn" with "सुन" printed beside it, linking home. The name is Latin in both languages; the
// Devanagari is the device's printed mark, so screen readers hear the link's name once.
export function Wordmark() {
  const { t } = useLang()
  return (
    <Link to="/" className="wordmark" lang="en" aria-label={t('nav.home')} viewTransition={!reducedMotion()}>
      <span className="wordmark-latin">Sunn</span>
      <span className="wordmark-hi" lang="hi" aria-hidden="true">
        सुन
      </span>
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

// A problem: the icon and the words, in ink. Color never carries it alone.
export function Alert({ error, id }) {
  const i18n = useLang()
  if (!error) return null
  return (
    <p className="alert" role="alert" id={id}>
      <Icon name="alert" className="alert-icon" />
      <span>{errorText(i18n, error)}</span>
    </p>
  )
}

// A short confirmation that something was saved, above the tab bar for a few seconds.
export function Toast({ children }) {
  return (
    <p className="toast" role="status">
      <Icon name="checkCircle" className="toast-icon" />
      <span>{children}</span>
    </p>
  )
}

// Two-state toggle in header: switches strictly between light and dark based on effective theme.
// Settings page retains full three-option selector (Light, Dark, Automatic).
export function ThemeToggle() {
  const { t } = useLang()
  const [theme, setTheme] = useTheme()
  const effective = resolveTheme(theme)
  const isDark = effective === 'dark'
  const next = isDark ? 'light' : 'dark'
  const label = t('theme.toggle', { theme: t(`theme.${next}`) })

  return (
    <button
      type="button"
      className="icon-button theme-toggle"
      onClick={() => setTheme(next)}
      aria-label={label}
      title={label}
    >
      <Icon name={isDark ? 'moon' : 'sun'} />
    </button>
  )
}

// The primary action: solid ink, at most one per screen. Orange is kept for the push button.
export function PrimaryButton({ children, icon, className = '', ...props }) {
  return (
    <button type="button" className={`button primary ${className}`} {...props}>
      {icon && <Icon name={icon} />}
      <span>{children}</span>
    </button>
  )
}

// A quieter action on a raised key.
export function Button({ children, icon, className = '', ...props }) {
  return (
    <button type="button" className={`button ${className}`} {...props}>
      {icon && <Icon name={icon} />}
      <span>{children}</span>
    </button>
  )
}

// One of a few, as keys in a well that scroll sideways when they don't fit (phrase filters).
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
          {option.mark && <span className="mark-urgent" aria-hidden="true" />}
          {option.label}
        </button>
      ))}
    </div>
  )
}
