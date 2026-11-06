import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useLang } from '../i18n/index.jsx'
import { reducedMotion } from './base.jsx'
import { Icon } from './icons.jsx'

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
            <Icon name="x" />
          </button>
        )}
        {open ? children : shown.current}
      </div>
    </dialog>
  )
}
