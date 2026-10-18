import { createContext, useContext, useEffect, useState } from 'react'
import en from './en.js'
import hi from './hi.js'

const STRINGS = { en, hi }
const KEY = 'sunn.lang'

function initialLang() {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved in STRINGS) return saved
  } catch {
    // storage blocked: fall back to the browser's language
  }
  return navigator.language?.toLowerCase().startsWith('hi') ? 'hi' : 'en'
}

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(initialLang)

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  function setLang(next) {
    setLangState(next)
    try {
      localStorage.setItem(KEY, next)
    } catch {
      // storage blocked: the choice lasts until the page is closed
    }
  }

  // t('key') is the string for the current language; {slot}s are filled from vars.
  // Lists (steps, faq) come back as they are written in en.js / hi.js.
  function t(key, vars) {
    let value = STRINGS[lang][key]
    if (value === undefined) {
      if (import.meta.env.DEV) console.warn(`missing ${lang} string: ${key}`)
      value = STRINGS.en[key] ?? key
    }
    if (vars && typeof value === 'string') value = value.replace(/\{(\w+)\}/g, (_, slot) => vars[slot] ?? '')
    return value
  }

  const has = (key) => key in STRINGS[lang]

  return <LanguageContext.Provider value={{ lang, setLang, t, has }}>{children}</LanguageContext.Provider>
}

export const useLang = () => useContext(LanguageContext)
