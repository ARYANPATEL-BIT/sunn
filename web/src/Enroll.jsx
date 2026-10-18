import { useEffect, useState } from 'react'
import * as api from './api.js'
import { Alert, RecordButton, T, useRecorder } from './ui.jsx'

const NEEDED = 3

// One phrase at a time, NEEDED saved recordings each. Every save is stored on the server,
// so leaving is pausing: coming back resumes at the first phrase that still needs recordings.
export default function Enroll({ userId, onPause }) {
  const [phrases, setPhrases] = useState(null)
  const [blob, setBlob] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const recorder = useRecorder(setBlob)

  useEffect(() => {
    api.listPhrases(userId).then(setPhrases, setError)
  }, [userId])

  if (!phrases) return <Alert error={error} />

  const done = phrases.filter((p) => p.enrolled >= NEEDED).length
  const phrase = phrases.find((p) => p.enrolled < NEEDED)

  async function save() {
    setSaving(true)
    setError(null)
    try {
      await api.enroll(userId, phrase.id, blob)
      setPhrases(phrases.map((p) => (p.id === phrase.id ? { ...p, enrolled: p.enrolled + 1 } : p)))
      setBlob(null)
    } catch (e) {
      setError(e)
    } finally {
      setSaving(false)
    }
  }

  function reRecord() {
    setBlob(null)
    recorder.toggle()
  }

  return (
    <section>
      <div className="progress-label">
        <T hi={`${done} / ${phrases.length} वाक्य पूरे`} en={`${done} of ${phrases.length} phrases done`} />
      </div>
      <div
        className="bar"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={phrases.length}
        aria-valuenow={done}
      >
        <div style={{ width: `${phrases.length ? (100 * done) / phrases.length : 0}%` }} />
      </div>

      {!phrase ? (
        <p className="big-message">
          <T hi="सब वाक्य सिखा दिए। अब 'बोलें' पर जाएँ।" en="All phrases are enrolled. Go to 'Speak'." />
        </p>
      ) : (
        <>
          <p className="phrase">{phrase.text}</p>
          <p className="count">
            <T hi={`रिकॉर्डिंग ${phrase.enrolled + 1} / ${NEEDED}`} en={`Recording ${phrase.enrolled + 1} of ${NEEDED}`} />
          </p>

          <Alert error={error || recorder.error} />
          {blob ? (
            <div className="stack">
              <button type="button" onClick={() => api.play(blob)}>
                <T hi="सुनें" en="Play back" />
              </button>
              <button type="button" onClick={reRecord} disabled={saving}>
                <T hi="फिर से बोलें" en="Re-record" />
              </button>
              <button type="button" className="primary" onClick={save} disabled={saving}>
                {saving ? <T hi="सहेज रहे हैं…" en="Saving…" /> : <T hi="सहेजें" en="Save" />}
              </button>
            </div>
          ) : (
            <RecordButton recorder={recorder} />
          )}

          <button type="button" className="quiet" onClick={onPause} disabled={recorder.recording || saving}>
            <T hi="रोकें, बाद में करें" en="Pause, continue later" />
          </button>
        </>
      )}
    </section>
  )
}
