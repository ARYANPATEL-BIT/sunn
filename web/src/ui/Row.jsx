import { Icon } from './icons.jsx'

// A switch: a well track that turns ink when on. Never orange. Its name comes from the row it
// sits in (labelledBy).
export function Toggle({ on, labelledBy, describedBy, ...props }) {
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

// A plate of rows: a title above, rows with hairlines between, a footnote below. With bare,
// the children bring their own plate (a radiogroup of Choices, a form).
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

// A settings row with a title, a line of help under it, and a switch at the end.
export function Row({ id, title, help, note, on, onClick, disabled }) {
  return (
    <div className="row settings-row">
      <span className="row-text">
        <span className="row-title" id={`${id}-label`}>
          {title}
        </span>
        <span className="row-sub" id={`${id}-help`}>
          {help}
        </span>
        {note && <span className="row-sub">{note}</span>}
      </span>
      <Toggle on={on} labelledBy={`${id}-label`} describedBy={`${id}-help`} onClick={onClick} disabled={disabled} />
    </div>
  )
}

// One choice of a few, as rows with a check at the end. A radiogroup of radios.
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
          <Icon name="check" className="choice-check" />
        </button>
      ))}
    </div>
  )
}
