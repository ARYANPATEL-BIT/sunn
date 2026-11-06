import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { speakProgress } from './quickstart.js'
import { useRecorder } from './record.jsx'
import {
  Alert, Band, Button, CONTEXT_BAND, failure, Grille, Icon, Label, Led, PrimaryButton, PushButton, RankedFace,
  RankedList, Readout, ReadoutRow, Sheet, useGo,
} from './ui/index.js'

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
        <PrimaryButton icon="mic" onClick={() => go('/app/enroll')}>
          {t('speak.goTeach')}
        </PrimaryButton>
      </section>
    )
  }

  const candidates = Array.isArray(result?.candidates)
    ? result.candidates.filter((c) => c && typeof c.text === 'string' && c.text.trim())
    : []
  const typed = spoken && !candidates.some((c) => isSameCandidate(c, spoken))
  const shown = typed ? [spoken] : candidates
  // The best guess (or the phrase typed in) is the readout's phrase; the others are ranked under it.
  const top = shown[0]
  const rest = typed ? [] : shown.slice(1)
  const problem = error || recorder.error

  const blobState = recorder.recording ? 'listening' : busy === 'listening' ? 'thinking' : problem && !typing ? 'error' : 'rest'
  const status = recorder.recording
    ? 'device.status_listening'
    : busy === 'listening'
      ? 'device.status_thinking'
      : problem && !typing
        ? 'device.status_error'
        : result
          ? shown.length
            ? 'device.status_result'
            : 'device.status_unknown'
          : 'device.status_ready'

  function said(c) {
    return isSameCandidate(spoken, c) ? t(busy === 'playing' ? 'speak.playing' : 'speak.played') : null
  }

  function urgentMark(c, tone = '') {
    return (
      c.urgent && (
        <span className={`urgent ${tone}`}>
          <span className="mark-urgent" aria-hidden="true" />
          {t('speak.urgent')}
        </span>
      )
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

      <div className="device speak-device">
        <Grille className="grille-strip" />

        <Readout
          blobState={blobState}
          level={recorder.level}
          top={
            <>
              <Label k={status} inline className="readout-status" />
              {top?.urgent && !typing && <Led on tone="sos" className="readout-sos" />}
            </>
          }
        >
          <div className="results" aria-live="polite">
            {result ? (
              <div className="result" key={result.sample_id}>
                {result.hypothesis && (
                  <ReadoutRow label="device.heard">
                    <p className="readout-heard">
                      <span lang={user.language}>“{result.hypothesis}”</span>
                    </p>
                  </ReadoutRow>
                )}
                <ReadoutRow label="device.understood">
                  {result.low_confidence && !typed && candidates.length > 0 && (
                    <p className="readout-note">{t('speak.maybe')}</p>
                  )}
                  {top ? (
                    <button
                      type="button"
                      className="candidate top"
                      onClick={() => choose(top)}
                      disabled={busy === 'listening'}
                      aria-pressed={isSameCandidate(spoken, top)}
                      aria-describedby="top-hint"
                    >
                      <span className="candidate-text" lang={user.language}>
                        {top.text}
                      </span>
                      {/* Named by the phrase alone; the urgent word and the hint are its description. */}
                      <span className="candidate-meta" id="top-hint" aria-hidden="true">
                        {urgentMark(top, 'on-screen')}
                        {top.composed && <span className="tag">{t('speak.composedBadge')}</span>}
                        <span className="candidate-hint">
                          <Icon name="volume" />
                          <span className={said(top) ? 'said' : undefined}>{said(top) || t('speak.tapToSay')}</span>
                        </span>
                      </span>
                    </button>
                  ) : (
                    <p className="readout-idle">{t('speak.unknown')}</p>
                  )}
                </ReadoutRow>
              </div>
            ) : (
              <ReadoutRow label="device.understood">
                <p className="readout-idle">{t('speak.idle')}</p>
              </ReadoutRow>
            )}
          </div>
        </Readout>

        {result && (
          <RankedList title={rest.length ? 'device.others' : undefined}>
            {rest.map((c, i) => (
              <button
                key={candidateKey(c, i + 1)}
                type="button"
                className="ranked-row candidate"
                onClick={() => choose(c)}
                disabled={busy === 'listening'}
                aria-pressed={isSameCandidate(spoken, c)}
              >
                <RankedFace n={i + 2} icon="volume">
                  <span className="candidate-text" lang={user.language}>
                    {c.text}
                  </span>
                  {(c.urgent || c.composed || said(c)) && (
                    <span className="candidate-meta">
                      {urgentMark(c)}
                      {c.composed && <span className="tag">{t('speak.composedBadge')}</span>}
                      {said(c) && <span className="said">{said(c)}</span>}
                    </span>
                  )}
                </RankedFace>
              </button>
            ))}
            <button
              type="button"
              className="ranked-row none-row"
              onClick={() => setTyping(true)}
              disabled={busy !== null}
              aria-haspopup="dialog"
            >
              <RankedFace icon="chevronRight">
                <span className="none-title">
                  <Icon name="pencilLine" />
                  {t(shown.length ? 'speak.noneOfThese' : 'speak.typeIt')}
                </span>
              </RankedFace>
            </button>
          </RankedList>
        )}

        {busy === 'playing' && (
          <div className="playback-bar">
            <span>{t('speak.playing')}</span>
            <Button className="small" icon="stop" onClick={stopPlayback} aria-label={t('speak.stopPlaying')}>
              {t('speak.stopPlaying')}
            </Button>
          </div>
        )}

        {fallbackUsed && (
          <p className="note" role="status">
            {t('speak.usingBrowserTts')}
          </p>
        )}

        {!typing && <Alert error={problem} />}

        {recorder.error?.kind === 'micDenied' && (
          <div className="help-card" role="region" aria-label={t('speak.micTroubleshootTitle')}>
            <p className="help-title">{t('speak.micTroubleshootTitle')}</p>
            <p className="help-body">{t('speak.micTroubleshootBody')}</p>
          </div>
        )}

        {problem && !typing && (
          <div className="actions">
            <Button icon="rotate" onClick={retry}>
              {t('speak.retry')}
            </Button>
          </div>
        )}

        <Band
          title="device.place"
          label={t('speak.context')}
          options={CONTEXT_BAND}
          value={context}
          onChange={setContext}
          disabled={recorder.recording || busy !== null}
        />

        <PushButton
          recorder={recorder}
          onClick={record}
          waiting={busy === 'listening'}
          disabled={busy !== null}
          label={result ? t('sun.again') : undefined}
        />
      </div>

      <Sheet open={typing} onClose={() => setTyping(false)} label={t(shown.length ? 'speak.noneOfThese' : 'speak.typeIt')}>
        <form className="sheet-form" onSubmit={submitNewText}>
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
          <Alert error={error} />
          <div className="actions">
            <Button onClick={() => setTyping(false)}>{t('speak.cancel')}</Button>
            <PrimaryButton type="submit" disabled={!newText.trim() || busy !== null}>
              {t('speak.sayIt')}
            </PrimaryButton>
          </div>
        </form>
      </Sheet>
    </section>
  )
}
