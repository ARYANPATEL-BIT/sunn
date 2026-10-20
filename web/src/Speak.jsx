import { RotateCcw, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { Alert, failure, Pill, Sun, useGo, useRecorder } from './ui.jsx'

const CONTEXT_LIST = ['any', 'home', 'hospital', 'market']

function candidateKey(c) {
  if (c.composed) return `composed-${c.template_id}-${c.slot_word_id}`
  return `phrase-${c.phrase_id || c.text}`
}

function isSameCandidate(a, b) {
  if (!a || !b) return false
  if (a.composed || b.composed) {
    return a.template_id === b.template_id && a.slot_word_id === b.slot_word_id
  }
  if (a.phrase_id && b.phrase_id) {
    return a.phrase_id === b.phrase_id
  }
  return a.text === b.text
}

export default function Speak() {
  const { t } = useLang()
  const { user } = useAuth()
  const go = useGo()
  const [context, setContext] = useState('any')
  const [learned, setLearned] = useState(null) // phrases with at least one enrollment recording
  const [result, setResult] = useState(null) // the /recognize response
  const [spoken, setSpoken] = useState(null) // { phrase_id, text } chosen for this result
  const [typing, setTyping] = useState(false)
  const [newText, setNewText] = useState('')
  const [busy, setBusy] = useState(null) // 'listening' while Prisma works, 'playing' while Timbre speaks
  const [error, setError] = useState(null)
  const confirmedSampleRef = useRef(null)

  const recorder = useRecorder((blob) =>
    run('listening', async () => {
      const response = await api.recognize(blob, context)
      if (!response.hypothesis?.trim()) throw failure('silent')
      setResult(response)
      confirmedSampleRef.current = null
    }),
  )

  useEffect(() => {
    api.listPhrases().then((phrases) => setLearned(phrases.filter((p) => p.enrolled > 0).length), setError)
    return () => {
      api.stopAudio()
    }
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
      api.stopAudio()
      setResult(null)
      setSpoken(null)
      setTyping(false)
      setNewText('')
      setError(null)
      confirmedSampleRef.current = null
    }
    recorder.toggle()
  }

  // Say the phrase aloud. Choosing a phrase also tells the bank what this recording was; a
  // composed one (template + slot word) has no phrase_id yet, and confirming it makes one.
  function choose(candidate) {
    if (busy === 'playing' && isSameCandidate(spoken, candidate)) {
      api.stopAudio()
      setBusy(null)
      return
    }

    run('playing', async () => {
      setSpoken(candidate)
      let confirmPromise = Promise.resolve()
      if (confirmedSampleRef.current !== result.sample_id) {
        const answer = candidate.composed
          ? { template_id: candidate.template_id, slot_word_id: candidate.slot_word_id }
          : { phrase_id: candidate.phrase_id }
        confirmPromise = api.confirm({ sample_id: result.sample_id, ...answer }).then(() => {
          confirmedSampleRef.current = result.sample_id
        })
      }
      try {
        await Promise.all([api.say(candidate.text), confirmPromise])
      } catch (e) {
        setError(e)
      }
    })
  }

  function submitNewText(e) {
    e.preventDefault()
    const text = newText.trim()
    if (!text) return
    run('playing', async () => {
      let confirmed = null
      try {
        confirmed = await api.confirm({ sample_id: result.sample_id, new_text: text })
        confirmedSampleRef.current = result.sample_id
      } catch (e) {
        setError(e)
        return
      }
      setSpoken(confirmed)
      setTyping(false)
      try {
        await api.say(confirmed.text)
      } catch (e) {
        setError(e)
      }
    })
  }

  function stopPlayback() {
    api.stopAudio()
    setBusy(null)
  }

  function retry() {
    setError(null)
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
  const typed = spoken && !candidates.some((c) => isSameCandidate(c, spoken))
  const shown = typed ? [spoken] : candidates

  return (
    <section className="screen speak">
      <h1 className="visually-hidden">{t('speak.title')}</h1>

      <div className="context-bar" role="radiogroup" aria-label={t('speak.context')}>
        {CONTEXT_LIST.map((ctx) => (
          <button
            key={ctx}
            type="button"
            role="radio"
            aria-checked={context === ctx}
            className={`context-pill ${context === ctx ? 'active' : ''}`}
            onClick={() => setContext(ctx)}
            disabled={recorder.recording || busy !== null}
          >
            {t(`speak.context_${ctx}`)}
          </button>
        ))}
      </div>

      <div className="results" aria-live="polite">
        {result && (
          <div className="stack" key={result.sample_id}>
            {result.hypothesis && (
              <p className="heard-raw">
                <span className="muted">{t('speak.heard')}</span>
                <span className="raw-text">“{result.hypothesis}”</span>
              </p>
            )}

            {result.low_confidence && !typed && candidates.length > 0 && (
              <p className="maybe">{t('speak.maybe')}</p>
            )}

            {shown.length === 0 && <p>{t('speak.unknown')}</p>}

            {shown.map((c, i) => {
              const isTop = i === 0 && !typed
              const isSelected = isSameCandidate(spoken, c)
              return (
                <button
                  key={candidateKey(c)}
                  type="button"
                  className={isTop ? 'candidate top' : 'candidate'}
                  onClick={() => choose(c)}
                  disabled={busy === 'listening'}
                  aria-pressed={isSelected}
                >
                  <div className="candidate-text-row">
                    <span lang={user.language}>{c.text}</span>
                    {c.urgent && (
                      <span className="urgent-badge" aria-label={t('speak.urgent')}>
                        {t('speak.urgent')}
                      </span>
                    )}
                  </div>
                  {isSelected && (
                    <span className="said">
                      {t(busy === 'playing' ? 'speak.playing' : 'speak.played')}
                    </span>
                  )}
                </button>
              )
            })}

            {busy === 'playing' && (
              <div className="playback-bar">
                <span>{t('speak.playing')}</span>
                <button
                  type="button"
                  className="pill-outline stop-playback-btn"
                  onClick={stopPlayback}
                  aria-label={t('speak.stopPlaying')}
                >
                  <Square size={13} fill="currentColor" strokeWidth={1.5} aria-hidden="true" />
                  <span>{t('speak.stopPlaying')}</span>
                </button>
              </div>
            )}

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
              <button
                type="button"
                className="link none"
                onClick={() => setTyping(true)}
                disabled={busy !== null}
              >
                {t(shown.length ? 'speak.noneOfThese' : 'speak.typeIt')}
              </button>
            )}
          </div>
        )}
      </div>

      <Alert error={error || recorder.error} />

      {(error || recorder.error) && (
        <div className="error-actions">
          <button type="button" className="pill-outline" onClick={retry}>
            <RotateCcw size={16} strokeWidth={1.5} aria-hidden="true" />
            <span>{t('speak.retry')}</span>
          </button>
        </div>
      )}

      <Sun
        recorder={recorder}
        onClick={record}
        waiting={busy === 'listening'}
        disabled={busy === 'playing'}
        compact={!!result}
        label={result ? t('sun.again') : undefined}
      />
    </section>
  )
}
