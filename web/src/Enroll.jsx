import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { NEEDED, needsRerecord, quickStart, ready } from './quickstart.js'
import { useRecorder } from './record.jsx'
import { Alert, Button, Grille, Label, PrimaryButton, PushButton, Readout, ReadoutRow, useGo } from './ui/index.js'

// One phrase at a time, NEEDED saved recordings each, the 10 quick-start phrases first. Every
// save is stored on the server, so leaving is pausing: coming back resumes at the first phrase
// that still needs recordings. Recording here is the same device as Speak: readout, blob, key.
export default function Enroll() {
  const { t } = useLang()
  const { user } = useAuth()
  const go = useGo()
  const { state } = useLocation()
  const [phrases, setPhrases] = useState(null)
  const [blob, setBlob] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const recorder = useRecorder(setBlob)

  async function run(action) {
    setBusy(true)
    setError(null)
    try {
      await action()
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const load = () => run(async () => setPhrases(await api.listPhrases()))
  useEffect(() => {
    load()
    return () => {
      api.stopAudio()
    }
  }, [])

  if (!phrases) {
    return (
      <section className="screen narrow">
        <Alert error={error} />
        {error && (
          <Button onClick={load} disabled={busy}>
            {t('error.retry')}
          </Button>
        )}
      </section>
    )
  }

  if (phrases.length === 0) {
    return (
      <section className="screen narrow empty-state">
        <h1 className="large-title">{t('enroll.empty')}</h1>
        {state?.phrasesFailed && <p className="note">{t('signup.phrasesFailed')}</p>}
        <p className="lede-sm">{t('enroll.emptyBody')}</p>
        <Alert error={error} />
        <PrimaryButton disabled={busy} onClick={() => run(async () => setPhrases(await api.loadDefaultPhrases()))}>
          {t(busy ? 'enroll.adding' : 'enroll.addDefaults')}
        </PrimaryButton>
      </section>
    )
  }

  const first = quickStart(phrases, user.language)
  const order = [...first, ...phrases.filter((p) => !first.includes(p))]
  const done = phrases.filter(ready).length
  const firstDone = first.filter(ready).length
  const phrase = order.find((p) => !ready(p))

  const progress = (
    <div className="learned">
      <Label k="device.learned" inline className="learned-label" />
      <span className="learned-count" aria-hidden="true">
        {done} / {phrases.length}
      </span>
      <div
        className="progress-line"
        role="progressbar"
        aria-label={t('enroll.progress')}
        aria-valuemin={0}
        aria-valuemax={phrases.length}
        aria-valuenow={done}
      >
        <div style={{ transform: `scaleX(${done / phrases.length})` }} />
      </div>
    </div>
  )

  if (!phrase) {
    return (
      <section className="screen narrow empty-state">
        {progress}
        <h1 className="large-title">{t('enroll.done')}</h1>
        <p className="lede-sm">{t('enroll.doneBody')}</p>
        <PrimaryButton icon="mic" onClick={() => go('/app/speak')}>
          {t('enroll.goSpeak')}
        </PrimaryButton>
      </section>
    )
  }

  function save() {
    run(async () => {
      await api.enroll(phrase.id, blob)
      setPhrases(
        phrases.map((p) =>
          p.id === phrase.id ? { ...p, enrolled: p.enrolled + 1, sample_count: p.sample_count + 1 } : p,
        ),
      )
      setBlob(null)
    })
  }

  const saved = Math.min(phrase.sample_count, NEEDED)
  const problem = error || recorder.error
  const blobState = recorder.recording ? 'listening' : busy ? 'thinking' : problem ? 'error' : 'rest'

  return (
    <section className="screen enroll">
      <div className="device enroll-device">
        <Grille className="grille-strip" />
        {progress}
        {first.length > 0 &&
          (firstDone < first.length ? (
            <p className="note">
              {t('enroll.quickStart')} {t('enroll.quickProgress', { n: firstDone, total: first.length })}
            </p>
          ) : (
            <p className="note">
              {t('enroll.quickDone')}{' '}
              <button type="button" className="text-button" onClick={() => go('/app/speak')}>
                {t('enroll.goSpeak')}
              </button>
            </p>
          ))}

        <Readout
          blobState={blobState}
          level={recorder.level}
          top={<span className="readout-step">{t('enroll.step', { n: done + 1, total: phrases.length })}</span>}
        >
          <ReadoutRow label="device.say">
            <h1 className="readout-phrase" lang={user.language}>
              <span className="visually-hidden">{t('enroll.say')}: </span>
              {phrase.text}
            </h1>
            {needsRerecord(phrase) && <p className="readout-note">{t('enroll.rerecord')}</p>}
          </ReadoutRow>
          <ReadoutRow label="device.saved">
            <p className="saved-meter" role="img" aria-label={t('enroll.saved', { n: phrase.sample_count, needed: NEEDED })}>
              {Array.from({ length: NEEDED }, (_, i) => (
                <span key={i} className={`segment ${i < saved ? 'on' : ''}`} />
              ))}
              <span className="saved-count" aria-hidden="true">
                {saved} / {NEEDED}
              </span>
            </p>
          </ReadoutRow>
        </Readout>

        <Alert error={problem} />
        <PushButton recorder={recorder} waiting={busy} disabled={busy} label={blob && t('sun.again')} />
        {blob && !recorder.recording && (
          <div className="actions enroll-actions">
            <Button icon="play" onClick={() => api.play(blob).catch(setError)} disabled={busy}>
              {t('enroll.play')}
            </Button>
            <PrimaryButton onClick={save} disabled={busy}>
              {t('enroll.save')}
            </PrimaryButton>
          </div>
        )}
      </div>
    </section>
  )
}
