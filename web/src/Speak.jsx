import { ChevronRight, Mic, PencilLine, RotateCcw, Square, Volume2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { speakProgress } from './quickstart.js'
import { RecordButton, useRecorder } from './record.jsx'
import { Alert, Chips, failure, ICON, Pill, Sheet, useGo } from './ui.jsx'

const CONTEXT_LIST = ['any', 'home', 'hospital', 'market']

function candidateKey(c, index = 0) {
  if (!c) return `candidate-empty-${index}`
  if (c.composed) return `composed-${c.template_id ?? 't'}-${c.slot_word_id ?? 'w'}-${index}`
  if (c.phrase_id != null) return `phrase-${c.phrase_id}-${index}`
  return `text-${c.text ?? ''}-${index}`
}

function isSameCandidate(a, b) {
  if (!a || !b) return false
  if (a.composed || b.composed) {
    return Boolean(a.composed && b.composed && a.template_id === b.template_id && a.slot_word_id === b.slot_word_id)
  }
  if (a.phrase_id != null || b.phrase_id != null) {
    return a.phrase_id != null && b.phrase_id != null && a.phrase_id === b.phrase_id
  }
  return Boolean(a.text && b.text && a.text.trim() === b.text.trim())
}

export default function Speak() {
  const { t } = useLang()
  const { user } = useAuth()
  const go = useGo()
  const [context, setContext] = useState('any')
  const [learned, setLearned] = useState(null) // speakProgress: the quick-start phrases ready so far
  const [result, setResult] = useState(null) // the /recognize response
  const [spoken, setSpoken] = useState(null) // { phrase_id, text } chosen for this result
  const [typing, setTyping] = useState(false)
  const [newText, setNewText] = useState('')
  const [busy, setBusy] = useState(null) // 'listening' while Prisma works, 'playing' while Timbre speaks
  const [error, setError] = useState(null)
  const [fallbackUsed, setFallbackUsed] = useState(false)
  const confirmedSampleRef = useRef(null)
  const confirmingSampleRef = useRef(null)
  const isMountedRef = useRef(true)
  const activeRecordIdRef = useRef(0)

  const recorder = useRecorder((blob) => {
    const recordId = ++activeRecordIdRef.current
    run('listening', async () => {
      const response = await api.recognize(blob, context)
      if (!isMountedRef.current || recordId !== activeRecordIdRef.current) return
      if (!response.hypothesis?.trim()) throw failure('silent')
      setResult(response)
      confirmedSampleRef.current = null
      confirmingSampleRef.current = null
    })
  })

  useEffect(() => {
    isMountedRef.current = true
    api.listPhrases().then((phrases) => {
      if (isMountedRef.current) setLearned(speakProgress(phrases, user.language))
    }, (err) => {
      if (isMountedRef.current) setError(err)
    })
    return () => {
      isMountedRef.current = false
      activeRecordIdRef.current++
      api.stopAudio()
    }
  }, [])

  async function run(kind, action) {
    if (!isMountedRef.current) return
    setBusy(kind)
    setError(null)
    try {
      await action()
    } catch (e) {
      if (isMountedRef.current) setError(e)
    } finally {
      if (isMountedRef.current) setBusy(null)
    }
  }

  function record() {
    if (busy !== null) return
    if (!recorder.recording) {
      activeRecordIdRef.current++
      api.stopAudio()
      setResult(null)
      setSpoken(null)
      setTyping(false)
      setNewText('')
      setError(null)
      setFallbackUsed(false)
      confirmedSampleRef.current = null
      confirmingSampleRef.current = null
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
      const sampleId = result?.sample_id
      let confirmed = false
      let confirmPromise = Promise.resolve()

      if (sampleId && confirmedSampleRef.current !== sampleId && confirmingSampleRef.current !== sampleId) {
        confirmingSampleRef.current = sampleId
        const answer = candidate.composed
          ? { template_id: candidate.template_id, slot_word_id: candidate.slot_word_id }
          : { phrase_id: candidate.phrase_id }
        confirmPromise = api
          .confirm({ sample_id: sampleId, ...answer })
          .then((res) => {
            confirmedSampleRef.current = sampleId
            confirmed = true
            return res
          })
          .finally(() => {
            confirmingSampleRef.current = null
          })
      } else {
        confirmed = true
      }

      try {
        const [playback] = await Promise.all([
          api.say(candidate.text, { fallback: true, language: user?.language }),
          confirmPromise,
        ])
        setSpoken(candidate)
        setFallbackUsed(Boolean(playback?.fallback))
      } catch (e) {
        setError(e)
        if (!confirmed && confirmedSampleRef.current !== sampleId) {
          setSpoken(null)
        }
      }
    })
  }

  function submitNewText(e) {
    e.preventDefault()
    const text = newText.trim()
    if (!text) return
    const sampleId = result?.sample_id
    run('playing', async () => {
      let confirmed = null
      if (sampleId && confirmedSampleRef.current !== sampleId && confirmingSampleRef.current !== sampleId) {
        confirmingSampleRef.current = sampleId
        try {
          confirmed = await api.confirm({ sample_id: sampleId, new_text: text })
          confirmedSampleRef.current = sampleId
        } catch (e) {
          setError(e)
          return
        } finally {
          confirmingSampleRef.current = null
        }
      }
      const targetPhrase = confirmed || { text }
      setSpoken(targetPhrase)
      setTyping(false)
      try {
        const playback = await api.say(targetPhrase.text, { fallback: true, language: user?.language })
        setFallbackUsed(Boolean(playback?.fallback))
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
    recorder.reset?.()
  }

  if (learned && !learned.open) {
    return (
      <section className="screen narrow empty-state">
        <h1 className="large-title">{t('speak.none')}</h1>
        <p className="lede-sm">{t('speak.noneBody', { n: learned.ready, total: learned.total })}</p>
        <Pill icon={Mic} onClick={() => go('/app/enroll')}>
          {t('speak.goTeach')}
        </Pill>
      </section>
    )
  }

  const candidates = Array.isArray(result?.candidates)
    ? result.candidates.filter((c) => c && typeof c.text === 'string' && c.text.trim())
    : []
  const typed = spoken && !candidates.some((c) => isSameCandidate(c, spoken))
  const shown = typed ? [spoken] : candidates
  // The best guess gets the big card; the others (or a typed phrase) are rows under it.
  const top = typed ? null : shown[0]
  const rest = typed ? shown : shown.slice(1)

  function candidateButton(c, i, isTop) {
    const isSelected = isSameCandidate(spoken, c)
    return (
      <button
        key={candidateKey(c, i)}
        type="button"
        className={isTop ? 'candidate top' : 'row candidate'}
        onClick={() => choose(c)}
        disabled={busy === 'listening'}
        aria-pressed={isSelected}
      >
        <span className="candidate-body">
          <span className="candidate-text" lang={user.language}>
            {c.text}
          </span>
          {(c.urgent || c.composed) && (
            <span className="badges">
              {c.urgent && (
                <span className="badge">
                  <span className="dot-red" aria-hidden="true" />
                  {t('speak.urgent')}
                </span>
              )}
              {c.composed && <span className="badge">{t('speak.composedBadge')}</span>}
            </span>
          )}
          {isSelected && <span className="said">{t(busy === 'playing' ? 'speak.playing' : 'speak.played')}</span>}
        </span>
        <Volume2 className="candidate-icon" {...ICON} />
      </button>
    )
  }

  return (
    <section className={`screen speak ${result ? 'has-result' : ''}`}>
      <h1 className="visually-hidden">{t('speak.title')}</h1>

      {/* Screen reader live announcements for speech states */}
      <div className="visually-hidden" aria-live="polite">
        {recorder.recording
          ? t('speak.statusRecording')
          : busy === 'listening'
            ? t('speak.statusListening')
            : spoken && busy === 'playing'
              ? t('speak.statusPlaying', { text: spoken.text })
              : spoken
                ? t('speak.statusSpoke', { text: spoken.text })
                : null}
      </div>

      <Chips
        label={t('speak.context')}
        options={CONTEXT_LIST.map((ctx) => ({ value: ctx, label: t(`speak.context_${ctx}`) }))}
        value={context}
        onChange={setContext}
        disabled={recorder.recording || busy !== null}
      />

      <div className="results" aria-live="polite">
        {result && (
          <div className="result" key={result.sample_id}>
            {result.hypothesis && (
              <p className="heard">
                {t('speak.heard')}{' '}
                <span className="raw-text" lang={user.language}>
                  “{result.hypothesis}”
                </span>
              </p>
            )}

            {result.low_confidence && !typed && candidates.length > 0 && <p className="maybe">{t('speak.maybe')}</p>}

            {shown.length === 0 && <p className="unknown">{t('speak.unknown')}</p>}

            {top && candidateButton(top, 0, true)}

            <div className="group alternates">
              {rest.map((c, i) => candidateButton(c, typed ? i : i + 1, false))}
              <button
                type="button"
                className="row none-row"
                onClick={() => setTyping(true)}
                disabled={busy !== null}
                aria-haspopup="dialog"
              >
                <PencilLine className="row-icon" {...ICON} />
                <span className="row-title">{t(shown.length ? 'speak.noneOfThese' : 'speak.typeIt')}</span>
                <ChevronRight className="row-chevron" {...ICON} />
              </button>
            </div>

            {busy === 'playing' && (
              <div className="playback-bar">
                <span>{t('speak.playing')}</span>
                <button type="button" className="button small" onClick={stopPlayback} aria-label={t('speak.stopPlaying')}>
                  <Square fill="currentColor" {...ICON} />
                  <span>{t('speak.stopPlaying')}</span>
                </button>
              </div>
            )}

            {fallbackUsed && (
              <p className="note" role="status">
                {t('speak.usingBrowserTts')}
              </p>
            )}
          </div>
        )}
      </div>

      {!typing && <Alert error={error || recorder.error} />}

      {recorder.error?.kind === 'micDenied' && (
        <div className="help-card" role="region" aria-label={t('speak.micTroubleshootTitle')}>
          <p className="help-title">{t('speak.micTroubleshootTitle')}</p>
          <p className="help-body">{t('speak.micTroubleshootBody')}</p>
        </div>
      )}

      {(error || recorder.error) && !typing && (
        <div className="actions">
          <button type="button" className="button" onClick={retry}>
            <RotateCcw {...ICON} />
            <span>{t('speak.retry')}</span>
          </button>
        </div>
      )}

      <RecordButton
        recorder={recorder}
        onClick={record}
        waiting={busy === 'listening'}
        disabled={busy !== null}
        compact={!!result}
        label={result ? t('sun.again') : undefined}
      />

      <Sheet open={typing} onClose={() => setTyping(false)} label={t(shown.length ? 'speak.noneOfThese' : 'speak.typeIt')}>
        <form className="sheet-form" onSubmit={submitNewText}>
          <div className="group">
            <div className="field-cell">
              <label htmlFor="new-text" className="field-label">
                {t('speak.typeLabel')}
              </label>
              <textarea
                id="new-text"
                lang={user.language}
                value={newText}
                onChange={(e) => setNewText(e.target.value)}
                rows={2}
                data-autofocus
              />
            </div>
          </div>
          <Alert error={error} />
          <div className="actions">
            <button type="button" className="button" onClick={() => setTyping(false)}>
              {t('speak.cancel')}
            </button>
            <Pill type="submit" disabled={!newText.trim() || busy !== null}>
              {t('speak.sayIt')}
            </Pill>
          </div>
        </form>
      </Sheet>
    </section>
  )
}
