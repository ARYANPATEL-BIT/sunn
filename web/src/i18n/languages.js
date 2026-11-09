// The interface languages, in the order the picker lists them. `native` is the name in its own
// script, `font` the Google font loaded for it (none: IBM Plex covers Latin and Devanagari).
// The script's font stack is picked in styles.css by :lang().
export const LANGUAGES = [
  { code: 'en', native: 'English', english: 'English', locale: 'en-IN' },
  { code: 'hi', native: 'हिन्दी', english: 'Hindi', locale: 'hi-IN' },
  { code: 'ta', native: 'தமிழ்', english: 'Tamil', locale: 'ta-IN', font: 'Noto Sans Tamil' },
  { code: 'te', native: 'తెలుగు', english: 'Telugu', locale: 'te-IN', font: 'Noto Sans Telugu' },
  { code: 'kn', native: 'ಕನ್ನಡ', english: 'Kannada', locale: 'kn-IN', font: 'Noto Sans Kannada' },
  { code: 'ml', native: 'മലയാളം', english: 'Malayalam', locale: 'ml-IN', font: 'Noto Sans Malayalam' },
  { code: 'mr', native: 'मराठी', english: 'Marathi', locale: 'mr-IN' },
  { code: 'gu', native: 'ગુજરાતી', english: 'Gujarati', locale: 'gu-IN', font: 'Noto Sans Gujarati' },
  { code: 'bn', native: 'বাংলা', english: 'Bengali', locale: 'bn-IN', font: 'Noto Sans Bengali' },
  { code: 'pa', native: 'ਪੰਜਾਬੀ', english: 'Punjabi', locale: 'pa-IN', font: 'Noto Sans Gurmukhi' },
]

// Read by a native speaker: the interface strings and the starter phrases
// (data/default_phrases_<code>.txt). The rest were machine-written and show "beta" in the picker.
export const REVIEWED = new Set(['en', 'hi'])

export const language = (code) => LANGUAGES.find((l) => l.code === code) ?? LANGUAGES[0]

// The second language on bilingual device labels: the interface language, or Hindi under English.
export const secondLang = (code) => (code === 'en' ? 'hi' : code)

// A date in the interface language. Some browsers have no month names for a language
// (Chromium has none for Punjabi and prints "M11"): then the numeric date, which reads the same
// in every language.
export function formatDate(date, locale, options) {
  const text = date.toLocaleDateString(locale, options)
  if (!/M\d/.test(text)) return text
  return date.toLocaleDateString(locale, { year: options.year, month: 'numeric', day: options.day })
}
