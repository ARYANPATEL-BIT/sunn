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
      <section>
        <h1>
          <T hi={`नमस्ते, ${user.name}`} en={`Hello, ${user.name}`} />
        </h1>
        <p>
          <T
            hi="अब रोज़ बोले जाने वाले वाक्य लोड करें। फिर आप हर वाक्य 3 बार बोलकर ऐप को सिखाएँगे।"
            en="Now load everyday phrases. Then you will teach the app by saying each phrase 3 times."
          />
        </p>
        <Alert error={error} />
        <button type="button" className="primary" onClick={loadPhrases} disabled={busy}>
          <T hi="वाक्य लोड करें" en="Load default phrases" />
        </button>
      </section>
    )
  }

  const canContinue = name.trim() && consent && !busy
  return (
    <form onSubmit={createUser}>
      <h1>
        <T hi="सुन" en="Sunn" />
      </h1>
      <label className="field">
        <T hi="नाम" en="Name" />
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
      </label>

      <div className="consent">
        <p>
          <T
            hi="यह ऐप आपकी आवाज़ रिकॉर्ड करता है ताकि वह आपकी बोली समझना सीख सके। रिकॉर्डिंग इसी कंप्यूटर पर रखी जाती हैं और पहचान के लिए Gnani की सेवा को भेजी जाती हैं।"
            en="The app records your voice so it can learn to understand your speech. Recordings are kept on this computer and sent to Gnani's service for recognition."
          />
        </p>
        <label className="check">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          <span>
            <T hi="मैं सहमत हूँ" en="I agree" />
          </span>
        </label>
      </div>

      <Alert error={error} />
      {!consent && (
        <p className="hint">
          <T hi="आगे बढ़ने के लिए सहमति ज़रूरी है।" en="Consent is needed to continue." />
        </p>
      )}
      <button type="submit" className="primary" disabled={!canContinue}>
        <T hi="आगे बढ़ें" en="Continue" />
      </button>
    </form>
  )
}
