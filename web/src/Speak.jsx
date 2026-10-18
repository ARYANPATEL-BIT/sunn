import { useEffect, useState } from 'react'
import * as api from './api.js'
import { Alert, failure, Sun, T, useRecorder } from './ui.jsx'

export default function Speak({ userId, navigate }) {
  const [learned, setLearned] = useState(null) // phrases with at least one enrollment recording
  const [result, setResult] = useState(null) // the /recognize response
  const [spoken, setSpoken] = useState(null) // { phrase_id, text } chosen for this result
  const [typing, setTyping] = useState(false)
  const [newText, setNewText] = useState('')
  const [busy, setBusy] = useState(null) // 'listening' while Prisma works, 'playing' while Timbre speaks
  const [error, setError] = useState(null)
  const recorder = useRecorder((blob) =>
    run('listening', async () => {
      const response = await api.recognize(userId, blob)
      if (!response.hypothesis?.trim()) throw failure('silent')
      setResult(response)
    }),
  )

  useEffect(() => {
    api.listPhrases(userId).then((phrases) => setLearned(phrases.filter((p) => p.enrolled > 0).length), setError)
  }, [userId])

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
        api.confirm(userId, { sample_id: result.sample_id, phrase_id: candidate.phrase_id })
      setSpoken(candidate)
      await Promise.all([api.say(candidate.text), confirmed])
    })
  }

  function submitNewText(e) {
    e.preventDefault()
    run('playing', async () => {
      const phrase = await api.confirm(userId, { sample_id: result.sample_id, new_text: newText.trim() })
      setSpoken(phrase)
      setTyping(false)
      await api.say(phrase.text)
    })
  }

  if (learned === 0) {
    return (
      <section className="screen narrow">
        <h1>
          <T hi="अभी कोई वाक्य नहीं सिखाया" en="no phrases learned yet" />
        </h1>
        <p>
          <T hi="पहले सीखें में कुछ वाक्य बोलकर सिखाएँ, फिर यहाँ बोलें।" en="teach a few phrases in learn first, then speak here." />
        </p>
        <button type="button" className="primary" onClick={() => navigate('/learn')}>
          <T hi="सीखें" en="learn" />
        </button>
      </section>
    )
  }

  const candidates = result?.candidates ?? []
  const typed = spoken && !candidates.some((c) => c.phrase_id === spoken.phrase_id)
  const shown = typed ? [spoken] : candidates

  return (
    <section className="screen speak">
      <h1 className="visually-hidden">
        <T hi="बोलें" en="speak" />
      </h1>

      <div className="results" aria-live="polite">
        {result && (
          <div className="stack" key={result.sample_id}>
            {result.low_confidence && !typed && candidates.length > 0 && (
              <p className="maybe">
                <T hi="शायद" en="maybe" />
              </p>
            )}
            {shown.length === 0 && (
              <p>
                <T
                  hi="यह वाक्य पहचान में नहीं आया। फिर से बोलिए, या नीचे सही वाक्य लिखें।"
                  en="this phrase wasn't recognized. speak again, or type the right phrase below."
                />
              </p>
            )}
            {shown.map((c, i) => (
              <button
                key={c.phrase_id}
                type="button"
                lang="hi"
                className={i === 0 ? 'candidate top' : 'candidate'}
                onClick={() => choose(c)}
                disabled={busy !== null}
              >
                {c.text}
                {spoken?.phrase_id === c.phrase_id && (
                  <span className="said">
                    {busy === 'playing' ? (
                      <T hi="सुना रहे हैं…" en="playing…" />
                    ) : (
                      <T hi="सुना दिया, फिर सुनने के लिए दबाएँ" en="played. tap to hear it again" />
                    )}
                  </span>
                )}
              </button>
            ))}

            {typing ? (
              <form className="stack" onSubmit={submitNewText}>
                <label className="field">
                  <T hi="सही वाक्य लिखें" en="type the right phrase" />
                  <textarea lang="hi" value={newText} onChange={(e) => setNewText(e.target.value)} rows={2} autoFocus />
                </label>
                <div className="actions">
                  <button type="button" className="secondary" onClick={() => setTyping(false)}>
                    <T hi="रहने दें" en="cancel" />
                  </button>
                  <button type="submit" className="primary" disabled={!newText.trim() || busy !== null}>
                    <T hi="बोलें" en="speak it" />
                  </button>
                </div>
              </form>
            ) : (
              <button type="button" className="secondary none" onClick={() => setTyping(true)} disabled={busy !== null}>
                {shown.length ? (
                  <T hi="इनमें से कोई नहीं" en="none of these" />
                ) : (
                  <T hi="सही वाक्य लिखें" en="type the phrase" />
                )}
              </button>
            )}
          </div>
        )}
      </div>

      <Alert error={error || recorder.error} />
      <Sun recorder={recorder} onClick={record} waiting={busy === 'listening'} disabled={busy === 'playing'} compact={!!result} />
    </section>
  )
}
