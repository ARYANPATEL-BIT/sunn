import { useEffect, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { Alert, failure, Pill, Sun, useGo, useRecorder } from './ui.jsx'

export default function Speak() {
  const { t } = useLang()
  const { user } = useAuth()
  const go = useGo()
  const [learned, setLearned] = useState(null) // phrases with at least one enrollment recording
  const [result, setResult] = useState(null) // the /recognize response
  const [spoken, setSpoken] = useState(null) // { phrase_id, text } chosen for this result
  const [typing, setTyping] = useState(false)
  const [newText, setNewText] = useState('')
  const [busy, setBusy] = useState(null) // 'listening' while Prisma works, 'playing' while Timbre speaks
  const [error, setError] = useState(null)
  const recorder = useRecorder((blob) =>
    run('listening', async () => {
      const response = await api.recognize(blob)
      if (!response.hypothesis?.trim()) throw failure('silent')
      setResult(response)
    }),
  )

  useEffect(() => {
    api.listPhrases().then((phrases) => setLearned(phrases.filter((p) => p.enrolled > 0).length), setError)
  }, [])

  async function run(kind, action) {
    setBusy(kind)
    setError(null)
    try {
      await action()
    } catch (e) {
      setError(e)
    } finally {
      setBusy(null)
    }
  }

  function record() {
    if (!recorder.recording) {
      setResult(null)
      setSpoken(null)
      setTyping(false)
      setNewText('')
      setError(null)
    }
    recorder.toggle()
  }

  // Say the phrase aloud. Choosing a phrase also tells the bank what this recording was.
  function choose(candidate) {
    run('playing', async () => {
      const confirmed =
        spoken?.phrase_id !== candidate.phrase_id &&
        api.confirm({ sample_id: result.sample_id, phrase_id: candidate.phrase_id })
      setSpoken(candidate)
      await Promise.all([api.say(candidate.text), confirmed])
    })
  }

  function submitNewText(e) {
    e.preventDefault()
    run('playing', async () => {
      const phrase = await api.confirm({ sample_id: result.sample_id, new_text: newText.trim() })
      setSpoken(phrase)
      setTyping(false)
      await api.say(phrase.text)
    })
  }

  if (learned === 0) {
    return (
      <section className="screen narrow">
        <h1>{t('speak.none')}</h1>
        <p className="muted">{t('speak.noneBody')}</p>
        <Pill icon={null} onClick={() => go('/app/enroll')}>
          {t('speak.goTeach')}
        </Pill>
      </section>
    )
  }

  const candidates = result?.candidates ?? []
  const typed = spoken && !candidates.some((c) => c.phrase_id === spoken.phrase_id)
  const shown = typed ? [spoken] : candidates

  return (
    <section className="screen speak">
      <h1 className="visually-hidden">{t('speak.title')}</h1>

      <div className="results" aria-live="polite">
        {result && (
          <div className="stack" key={result.sample_id}>
            {result.low_confidence && !typed && candidates.length > 0 && <p className="maybe">{t('speak.maybe')}</p>}
            {shown.length === 0 && <p>{t('speak.unknown')}</p>}
            {shown.map((c, i) => (
              <button
                key={c.phrase_id}
                type="button"
                className={i === 0 ? 'candidate top' : 'candidate'}
                onClick={() => choose(c)}
                disabled={busy !== null}
              >
                <span lang={user.language}>{c.text}</span>
                {spoken?.phrase_id === c.phrase_id && (
                  <span className="said">{t(busy === 'playing' ? 'speak.playing' : 'speak.played')}</span>
                )}
              </button>
            ))}

            {typing ? (
              <form className="stack" onSubmit={submitNewText}>
                <div className="field">
                  <label htmlFor="new-text">{t('speak.typeLabel')}</label>
                  <textarea
                    id="new-text"
                    lang={user.language}
                    value={newText}
                    onChange={(e) => setNewText(e.target.value)}
                    rows={2}
                    autoFocus
                  />
                </div>
                <div className="actions">
                  <button type="button" className="pill-outline" onClick={() => setTyping(false)}>
                    {t('speak.cancel')}
                  </button>
                  <Pill type="submit" icon={null} disabled={!newText.trim() || busy !== null}>
                    {t('speak.sayIt')}
                  </Pill>
                </div>
              </form>
            ) : (
              <button type="button" className="link none" onClick={() => setTyping(true)} disabled={busy !== null}>
                {t(shown.length ? 'speak.noneOfThese' : 'speak.typeIt')}
              </button>
            )}
          </div>
        )}
      </div>

      <Alert error={error || recorder.error} />
      <Sun
        recorder={recorder}
        onClick={record}
        waiting={busy === 'listening'}
        disabled={busy === 'playing'}
        compact={!!result}
      />
    </section>
  )
}
