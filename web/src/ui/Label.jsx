import { useLang } from '../i18n/index.jsx'

// A label printed on the device: Hindi and English, always both, like an Indian radio's
// panel. English is mono uppercase. The language the interface is not in is aria-hidden, so a
// screen reader hears it once. `inline` sets them on one line with a separator.
export function Label({ k, inline, className = '', as: Tag = 'span', ...props }) {
  const { lang, bi } = useLang()
  const { en, hi } = bi(k)
  return (
    <Tag className={`label ${inline ? 'inline' : 'stacked'} ${className}`} {...props}>
      <span className="label-hi" lang="hi" aria-hidden={lang !== 'hi' || undefined}>
        {hi}
      </span>
      {inline && (
        <span className="label-sep" aria-hidden="true">
          ·
        </span>
      )}
      <span className="label-en" lang="en" aria-hidden={lang !== 'en' || undefined}>
        {en}
      </span>
    </Tag>
  )
}

// The speaker grille: holes on a 10px grid. Decorative.
export function Grille({ className = '' }) {
  return <div className={`grille ${className}`} aria-hidden="true" />
}

// The listening light. Its meaning is always also in text beside it.
export function Led({ on, tone = 'signal', className = '' }) {
  return <span className={`led ${tone} ${on ? 'on' : ''} ${className}`} aria-hidden="true" />
}
