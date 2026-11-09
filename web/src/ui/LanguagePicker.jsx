import { useEffect, useRef, useState } from 'react'
import { useLang } from '../i18n/index.jsx'
import { language, LANGUAGES, REVIEWED } from '../i18n/languages.js'
import { Icon } from './icons.jsx'
import { Sheet } from './Sheet.jsx'

const PHONE = '(max-width: 47.99rem)'

// Under each language's own name: its English name (none under English itself), and "beta"
// while no native speaker has read it. For lists of choices (Settings, onboarding) as well as the picker.
export function LanguageSub({ code }) {
  const { t } = useLang()
  return (
    <>
      {code !== 'en' && <span lang="en">{language(code).english}</span>}
      {!REVIEWED.has(code) && <span className="lang-beta"> · {t('lang.beta')}</span>}
    </>
  )
}

export const languageOptions = () =>
  LANGUAGES.map((l) => ({ value: l.code, label: l.native, lang: l.code, sub: <LanguageSub code={l.code} /> }))

// The interface language: a key printed with the current language's own name, opening all ten
// as a listbox, in a bottom sheet on phones and a small menu on wider screens. Arrow keys move,
// Enter or Space picks, Escape closes, and focus goes back to the key.
export function LanguagePicker() {
  const { lang, setLang, t } = useLang()
  const [open, setOpen] = useState(null) // null, 'sheet' or 'menu'
  const root = useRef(null)
  const button = useRef(null)

  function close() {
    setOpen(null)
    button.current?.focus()
  }

  function choose(code) {
    setLang(code)
    close()
  }

  // The menu closes when a click or the focus goes anywhere else.
  useEffect(() => {
    if (open !== 'menu') return
    const away = (e) => root.current && !root.current.contains(e.target) && setOpen(null)
    document.addEventListener('pointerdown', away)
    document.addEventListener('focusin', away)
    return () => {
      document.removeEventListener('pointerdown', away)
      document.removeEventListener('focusin', away)
    }
  }, [open])

  const label = t('lang.label')
  const list = <LanguageList value={lang} label={label} onChoose={choose} onClose={close} />
  return (
    <div className="lang-picker" ref={root}>
      <button
        ref={button}
        type="button"
        className="lang-button"
        aria-haspopup="listbox"
        aria-expanded={Boolean(open)}
        aria-label={`${label}: ${language(lang).native}`}
        onClick={() => {
          button.current.focus() // so the sheet hands focus back here, in every browser
          setOpen(open ? null : matchMedia(PHONE).matches ? 'sheet' : 'menu')
        }}
      >
        <span lang={lang}>{language(lang).native}</span>
        <Icon name="chevronDown" />
      </button>
      {open === 'menu' && <div className="lang-menu">{list}</div>}
      <Sheet open={open === 'sheet'} onClose={() => setOpen(null)} label={label} closable>
        <h2 className="sheet-title">{label}</h2>
        {list}
      </Sheet>
    </div>
  )
}

function LanguageList({ value, label, onChoose, onClose }) {
  const { t } = useLang()
  const list = useRef(null)

  useEffect(() => {
    list.current.querySelector('[aria-selected="true"]')?.focus()
  }, [])

  function onKeyDown(e) {
    const options = [...list.current.querySelectorAll('[role="option"]')]
    const i = options.indexOf(document.activeElement)
    const to = { ArrowDown: i + 1, ArrowUp: i - 1, Home: 0, End: options.length - 1 }[e.key]
    if (to !== undefined) {
      e.preventDefault()
      options[(to + options.length) % options.length].focus()
    } else if ((e.key === 'Enter' || e.key === ' ') && i >= 0) {
      e.preventDefault()
      onChoose(options[i].dataset.code)
    } else if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
    }
  }

  return (
    <div className="lang-list-wrap">
      <ul ref={list} className="lang-list" role="listbox" aria-label={label} onKeyDown={onKeyDown}>
        {LANGUAGES.map(({ code, native }) => (
          <li
            key={code}
            role="option"
            className="lang-option"
            data-code={code}
            aria-selected={code === value}
            tabIndex={code === value ? 0 : -1}
            data-autofocus={code === value || undefined}
            onClick={() => onChoose(code)}
          >
            <span className="lang-name">
              <span className="lang-native" lang={code}>
                {native}
              </span>
              <span className="lang-english">
                <LanguageSub code={code} />
              </span>
            </span>
            <Icon name="check" className="choice-check" />
          </li>
        ))}
      </ul>
      <p className="lang-note">{t('lang.betaNote')}</p>
    </div>
  )
}
