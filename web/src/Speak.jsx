import { useState } from 'react'
import * as api from './api.js'
import { Alert, RecordButton, T, useRecorder } from './ui.jsx'

export default function Speak({ userId }) {
  const [result, setResult] = useState(null) // the /recognize response
  const [spoken, setSpoken] = useState(null) // { phrase_id, text } that was confirmed and said
  const [typing, setTyping] = useState(false)
  const [newText, setNewText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const recorder = useRecorder((blob) => run(async () => setResult(await api.recognize(userId, blob))))

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

  function choose(candidate) {
    setSpoken(candidate)
    run(() =>
      Promise.all([
        api.say(candidate.text),
        api.confirm(userId, { sample_id: result.sample_id, phrase_id: candidate.phrase_id }),
      ]),
    )
  }

  function submitNewText(e) {
    e.preventDefault()
    run(async () => {
      const phrase = await api.confirm(userId, { sample_id: result.sample_id, new_text: newText.trim() })
      setSpoken(phrase)
      setTyping(false)
      await api.say(phrase.text)
    })
  }

  const candidates = result?.candidates ?? []
  const typed = spoken && !candidates.some((c) => c.phrase_id === spoken.phrase_id)

  return (
    <section>
      <RecordButton recorder={recorder} onClick={record} disabled={busy && !result} className="giant" />
      <Alert error={error || recorder.error} />

      {busy && !result && (
        <p className="big-message" role="status">
          <T hi="समझ रहे हैं…" en="Working it out…" />
        </p>
      )}

      {result && (
        <div className="stack" aria-live="polite">
          {typed && (
            <button type="button" className="candidate top chosen" onClick={() => run(() => api.say(spoken.text))}>
              {spoken.text}
            </button>
          )}
          {candidates.length === 0 && !typed && (
            <p className="big-message">
              <T hi="कोई वाक्य नहीं मिला।" en="No phrase found." />
            </p>
          )}
          {result.low_confidence && candidates.length > 0 && (
            <p className="maybe">
              <T hi="शायद" en="Maybe" />
            </p>
          )}
          {candidates.map((c, i) => (
            <button
              key={c.phrase_id}
              type="button"
              className={`candidate ${i === 0 ? 'top' : ''} ${spoken?.phrase_id === c.phrase_id ? 'chosen' : ''}`}
              onClick={() => choose(c)}
              disabled={busy}
            >
              {c.text}
            </button>
          ))}

          {typing ? (
            <form className="stack" onSubmit={submitNewText}>
              <label className="field">
                <T hi="सही वाक्य लिखें" en="Type the correct phrase" />
                <textarea value={newText} onChange={(e) => setNewText(e.target.value)} rows={2} autoFocus />
              </label>
              <button type="submit" className="primary" disabled={!newText.trim() || busy}>
                <T hi="बोलें" en="Speak it" />
              </button>
            </form>
          ) : (
            <button type="button" onClick={() => setTyping(true)} disabled={busy}>
              <T hi="इनमें से कोई नहीं" en="None of these" />
            </button>
          )}
        </div>
      )}
    </section>
  )
}
