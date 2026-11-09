import { useLang } from '../i18n/index.jsx'
import { Label } from './Label.jsx'

// The band selector: keys in a recessed well, each printed in the interface language (Hindi
// under English) over English, the chosen key raised. A radiogroup; each key is named in the interface language only.
export function Band({ title, label, options, value, onChange, disabled, still }) {
  const { t, bi } = useLang()
  return (
    <div className="band">
      {title && <Label k={title} inline className="band-title" />}
      <div className="band-well" role={still ? undefined : 'radiogroup'} aria-label={still ? undefined : label}>
        {options.map((option) => {
          const words = bi(option.k)
          const on = value === option.value
          const face = (
            <>
              <span className="band-local" lang={words.second} aria-hidden="true">
                {words.local}
              </span>
              <span className="band-en" lang="en" aria-hidden="true">
                {words.en}
              </span>
            </>
          )
          return still ? (
            <span key={option.value} className={`band-key ${on ? 'on' : ''}`} aria-hidden="true">
              {face}
            </span>
          ) : (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={on}
              aria-label={t(option.k)}
              className={`band-key ${on ? 'on' : ''}`}
              onClick={() => onChange(option.value)}
              disabled={disabled}
            >
              {face}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export const CONTEXT_BAND = ['any', 'home', 'hospital', 'market'].map((value) => ({ value, k: `speak.context_${value}` }))
