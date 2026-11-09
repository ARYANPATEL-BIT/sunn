import { createContext, useContext, useEffect, useState } from 'react'
import en from './en.js'
import hi from './hi.js'
import { language, LANGUAGES, secondLang } from './languages.js'

// English and Hindi come with the app; the others are fetched the first time they are chosen.
const STRINGS = { en, hi }
const LOAD = {
  ta: () => import('./ta.js'),
  te: () => import('./te.js'),
  kn: () => import('./kn.js'),
  ml: () => import('./ml.js'),
  mr: () => import('./mr.js'),
  gu: () => import('./gu.js'),
  bn: () => import('./bn.js'),
  pa: () => import('./pa.js'),
}
const CODES = new Set(LANGUAGES.map((l) => l.code))
const loadStrings = async (code) => {
  if (!STRINGS[code]) STRINGS[code] = (await LOAD[code]()).default
}
const KEY = 'sunn.lang'

// A saved choice, else the first browser language that is one of ours, else English.
function initialLang() {
  try {
    const saved = localStorage.getItem(KEY)
    if (CODES.has(saved)) return saved
  } catch {
    // storage blocked: fall back to the browser's language
  }
  const wanted = navigator.languages?.length ? navigator.languages : [navigator.language]
  for (const tag of wanted) {
    const code = tag?.toLowerCase().split('-')[0]
    if (CODES.has(code)) return code
  }
  return 'en'
}

// Only the active script's font is fetched, once; Latin and Devanagari come with index.html.
function loadFont(code) {
  const family = language(code).font
  if (!family || document.querySelector(`link[data-font="${code}"]`)) return
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.dataset.font = code
  link.href = `https://fonts.googleapis.com/css2?family=${family.replaceAll(' ', '+')}:wght@400;500;600;700&display=swap`
  document.head.append(link)
}

const warned = new Set()
const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(initialLang)
  const [, setLoaded] = useState(0)
  const ready = lang in STRINGS

  useEffect(() => {
    document.documentElement.lang = lang
    loadFont(lang)
    if (!ready) loadStrings(lang).then(() => setLoaded((n) => n + 1), () => setLangState('en'))
  }, [lang, ready])

  // The interface switches once the language's strings are here, so it never shows half of each.
  function setLang(next) {
    try {
      localStorage.setItem(KEY, next)
    } catch {
      // storage blocked: the choice lasts until the page is closed
    }
    loadStrings(next).then(() => setLangState(next), () => {})
  }

  // t('key') is the string for the current language, or the English one if it is missing;
  // {slot}s are filled from vars. Lists (steps, faq) come back as they are written.
  function t(key, vars) {
    let value = STRINGS[lang][key]
    if (value === undefined) {
      if (import.meta.env.DEV && !warned.has(`${lang}:${key}`)) {
        warned.add(`${lang}:${key}`)
        console.warn(`missing ${lang} string: ${key}`)
      }
      value = STRINGS.en[key] ?? key
    }
    if (vars && typeof value === 'string') value = value.replace(/\{(\w+)\}/g, (_, slot) => vars[slot] ?? '')
    return value
  }

  const has = (key) => key in STRINGS[lang]

  // Two languages at once, for labels printed on the device (DESIGN.md: Label): English, and
  // the interface language (Hindi when the interface is English).
  const second = secondLang(lang)
  const bi = (key) => ({ en: STRINGS.en[key] ?? key, local: STRINGS[second][key] ?? STRINGS.en[key] ?? key, second })

  if (!ready) return null
  return (
    <LanguageContext.Provider value={{ lang, setLang, t, has, bi, locale: language(lang).locale }}>
      {children}
    </LanguageContext.Provider>
  )
}

export const useLang = () => useContext(LanguageContext)
