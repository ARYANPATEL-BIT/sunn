import { useEffect, useState } from 'react'
import * as api from './api.js'
import { Alert, Sun, T, useRecorder } from './ui.jsx'

const NEEDED = 3

// One phrase at a time, NEEDED saved recordings each. Every save is stored on the server,
// so leaving is pausing: coming back resumes at the first phrase that still needs recordings.
export default function Enroll({ userId, navigate }) {
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

  const load = () => run(async () => setPhrases(await api.listPhrases(userId)))
  useEffect(() => {
    load()
  }, [userId])

  if (!phrases) {
    return (
      <section className="screen narrow">
        <Alert error={error} />
        {error && (
          <button type="button" className="secondary" onClick={load} disabled={busy}>
            <T hi="फिर से कोशिश करें" en="try again" />
          </button>
        )}
      </section>
    )
  }

  if (phrases.length === 0) {
    return (
      <section className="screen narrow">
        <h1>
          <T hi="अभी कोई वाक्य नहीं है" en="no phrases yet" />
        </h1>
        <p>
          <T hi="पहले रोज़ के वाक्य जोड़ें, फिर उन्हें बोलकर सिखाएँ।" en="add the everyday phrases first, then teach them by speaking." />
        </p>
        <Alert error={error} />
        <button
          type="button"
          className="primary"
          disabled={busy}
          onClick={() => run(async () => setPhrases(await api.loadDefaultPhrases(userId)))}
        >
          <T hi="रोज़ के वाक्य जोड़ें" en="add everyday phrases" />
        </button>
      </section>
    )
  }

  const done = phrases.filter((p) => p.enrolled >= NEEDED).length
  const phrase = phrases.find((p) => p.enrolled < NEEDED)

  const progress = (
    <div className="hairline" role="progressbar" aria-label="सीखे गए वाक्य" aria-valuemin={0} aria-valuemax={phrases.length} aria-valuenow={done}>
      <div style={{ transform: `scaleX(${done / phrases.length})` }} />
    </div>
  )

  if (!phrase) {
    return (
      <section className="screen narrow">
        {progress}
        <h1>
          <T hi="सब वाक्य सीख लिए" en="all phrases learned" />
        </h1>
        <p>
          <T hi="अब बोलें में जाकर कोई भी वाक्य बोलिए।" en="now go to speak and say any of them." />
        </p>
        <button type="button" className="primary" onClick={() => navigate('/speak')}>
          <T hi="बोलें" en="speak" />
        </button>
      </section>
    )
  }

  function save() {
    run(async () => {
      await api.enroll(userId, phrase.id, blob)
      setPhrases(phrases.map((p) => (p.id === phrase.id ? { ...p, enrolled: p.enrolled + 1 } : p)))
      setBlob(null)
    })
  }

  return (
    <section className="screen enroll">
      {progress}
      <h1 className="phrase" lang="hi">
        {phrase.text}
      </h1>
      <p className="dots" role="img" aria-label={`रिकॉर्डिंग ${phrase.enrolled} / ${NEEDED} सहेजी गईं`}>
        {Array.from({ length: NEEDED }, (_, i) => (
          <span key={i} className={i < phrase.enrolled ? 'saved' : ''} />
        ))}
      </p>
      <p className="step">
        <T hi={`वाक्य ${done + 1} / ${phrases.length}`} en={`phrase ${done + 1} of ${phrases.length}`} />
      </p>

      <Alert error={error || recorder.error} />
      <Sun
        recorder={recorder}
        compact
        waiting={busy}
        disabled={busy}
        label={blob && <T hi="फिर से बोलें" en="record again" />}
      />
      {blob && !recorder.recording && (
        <div className="actions">
          <button type="button" className="secondary" onClick={() => api.play(blob).catch(setError)} disabled={busy}>
            <T hi="सुनें" en="play back" />
          </button>
          <button type="button" className="primary" onClick={save} disabled={busy}>
            <T hi="सहेजें" en="save" />
          </button>
        </div>
      )}
    </section>
  )
}
