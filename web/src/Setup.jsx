import { useState } from 'react'
import * as api from './api.js'
import { Alert, T } from './ui.jsx'

// Create the user, then load the default phrases. onDone(userId) once both are done.
export default function Setup({ onDone }) {
  const [name, setName] = useState('')
  const [consent, setConsent] = useState(false)
  const [user, setUser] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

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

  function createUser(e) {
    e.preventDefault()
    run(async () => setUser(await api.createUser(name.trim())))
  }

  function loadPhrases() {
    run(async () => {
      await api.loadDefaultPhrases(user.id)
      onDone(user.id)
    })
  }

  if (user) {
    return (
      <section className="screen narrow">
        <h1>
          <T hi={`नमस्ते, ${user.name}`} en={`hello, ${user.name}`} />
        </h1>
        <p>
          <T
            hi="अब रोज़ के वाक्य जोड़ें। फिर हर वाक्य तीन बार बोलकर Sunn को अपनी बोली सिखाएँ।"
            en="now add everyday phrases. then say each one three times to teach Sunn your speech."
          />
        </p>
        <Alert error={error} />
        <button type="button" className="primary" onClick={loadPhrases} disabled={busy}>
          {busy ? <T hi="जोड़ रहे हैं…" en="adding…" /> : <T hi="रोज़ के वाक्य जोड़ें" en="add everyday phrases" />}
        </button>
      </section>
    )
  }

  const canContinue = name.trim() && consent && !busy
  return (
    <form className="screen narrow" onSubmit={createUser}>
      <h1>
        <T hi="नमस्ते" en="hello" />
      </h1>
      <label className="field">
        <T hi="नाम" en="name" />
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
      </label>

      <p>
        <T
          hi="Sunn आपकी आवाज़ रिकॉर्ड करता है ताकि आपकी बोली समझना सीख सके। रिकॉर्डिंग इसी कंप्यूटर पर रहती हैं और पहचान के लिए Gnani को भेजी जाती हैं।"
          en="Sunn records your voice to learn how you speak. recordings stay on this computer and are sent to Gnani for recognition."
        />
      </p>
      <label className="check">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
        <span>
          <T hi="मैं सहमत हूँ" en="i agree" />
        </span>
      </label>

      <Alert error={error} />
      <button type="submit" className="primary" disabled={!canContinue} aria-describedby="setup-hint">
        {busy ? <T hi="बना रहे हैं…" en="creating…" /> : <T hi="आगे बढ़ें" en="continue" />}
      </button>
      {!canContinue && !busy && (
        <p className="hint" id="setup-hint">
          <T hi="आगे बढ़ने के लिए नाम लिखें और सहमति दें।" en="write a name and agree to continue." />
        </p>
      )}
    </form>
  )
}
