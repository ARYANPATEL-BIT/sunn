import { Mic, Play } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { NEEDED, needsRerecord, quickStart, ready } from './quickstart.js'
import { RecordButton, useRecorder } from './record.jsx'
import { Alert, ICON, Pill, useGo } from './ui.jsx'

// One phrase at a time, NEEDED saved recordings each, the 10 quick-start phrases first. Every
// save is stored on the server, so leaving is pausing: coming back resumes at the first phrase
// that still needs recordings.
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
          <button type="button" className="button" onClick={load} disabled={busy}>
            {t('error.retry')}
          </button>
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
        <Pill disabled={busy} onClick={() => run(async () => setPhrases(await api.loadDefaultPhrases()))}>
          {t(busy ? 'enroll.adding' : 'enroll.addDefaults')}
        </Pill>
      </section>
    )
  }

  const first = quickStart(phrases, user.language)
  const order = [...first, ...phrases.filter((p) => !first.includes(p))]
  const done = phrases.filter(ready).length
  const firstDone = first.filter(ready).length
  const phrase = order.find((p) => !ready(p))

  const progress = (
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
  )

  if (!phrase) {
    return (
      <section className="screen narrow empty-state">
        {progress}
        <h1 className="large-title">{t('enroll.done')}</h1>
        <p className="lede-sm">{t('enroll.doneBody')}</p>
        <Pill icon={Mic} onClick={() => go('/app/speak')}>
          {t('enroll.goSpeak')}
        </Pill>
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

  return (
    <section className="screen enroll">
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

      <div className="enroll-phrase">
        <p className="step">{t('enroll.step', { n: done + 1, total: phrases.length })}</p>
        <h1 className="phrase" lang={user.language}>
          <span className="visually-hidden">{t('enroll.say')}: </span>
          {phrase.text}
        </h1>
        {needsRerecord(phrase) && <p className="note">{t('enroll.rerecord')}</p>}
        <p className="dots" role="img" aria-label={t('enroll.saved', { n: phrase.sample_count, needed: NEEDED })}>
          {Array.from({ length: NEEDED }, (_, i) => (
            <span key={i} className={i < phrase.sample_count ? 'saved' : ''} />
          ))}
        </p>
      </div>

      <Alert error={error || recorder.error} />
      <RecordButton recorder={recorder} waiting={busy} disabled={busy} label={blob && t('sun.again')} />
      <div className="actions enroll-actions">
        {blob && !recorder.recording && (
          <>
            <button type="button" className="button" onClick={() => api.play(blob).catch(setError)} disabled={busy}>
              <Play {...ICON} />
              <span>{t('enroll.play')}</span>
            </button>
            <Pill onClick={save} disabled={busy}>
              {t('enroll.save')}
            </Pill>
          </>
        )}
      </div>
    </section>
  )
}
