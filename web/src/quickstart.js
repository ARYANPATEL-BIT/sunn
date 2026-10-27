// The 10 everyday phrases to record first (help, pain, needs), exactly as in
// data/default_phrases_*.txt. Speak opens once every one of them the user has is ready.
export const NEEDED = 3
const QUICK_START = {
  hi: [
    'मदद चाहिए',
    'दर्द हो रहा है',
    'पानी चाहिए',
    'बाथरूम जाना है',
    'दवाई दे दो',
    'डॉक्टर को बुलाओ',
    'सांस लेने में तकलीफ़ है',
    'भूख लगी है',
    'ठंड लग रही है',
    'मुझे उठा दो',
  ],
  en: [
    'I need help',
    "I'm in pain",
    'I need water',
    'I need the bathroom',
    'Give me my medicine',
    'Call the doctor',
    "I can't breathe properly",
    "I'm hungry",
    'I feel cold',
    'Help me sit up',
  ],
}

// sample_count counts recordings in the language the user speaks now, the only ones Sunn
// matches against; a phrase recorded only in another language has 0 and needs recording again.
export const ready = (phrase) => phrase.sample_count >= NEEDED
export const needsRerecord = (phrase) => phrase.sample_count === 0 && phrase.enrolled > 0

// The user's quick-start phrases, in that order: the ones they still have.
export function quickStart(phrases, language) {
  return (QUICK_START[language] || []).map((text) => phrases.find((p) => p.text === text)).filter(Boolean)
}

// { ready, total } toward opening Speak. Without any quick-start phrase (all deleted, or a
// custom list), one phrase with a recording is enough.
export function speakProgress(phrases, language) {
  const first = quickStart(phrases, language)
  if (!first.length) {
    const any = phrases.some((p) => p.sample_count > 0)
    return { ready: any ? 1 : 0, total: 1, open: any }
  }
  const done = first.filter(ready).length
  return { ready: done, total: first.length, open: done === first.length }
}
