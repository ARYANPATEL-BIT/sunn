import { T } from './ui.jsx'

const STEPS = [
  { hi: 'कुछ वाक्य रिकॉर्ड करें', en: 'record a few phrases' },
  { hi: 'बोलें', en: 'speak' },
  { hi: 'साफ़ सुने जाएँ, अपनी आवाज़ में', en: 'be heard clearly, in your own voice' },
]

export default function Landing({ onStart }) {
  return (
    <div className="landing">
      <section className="hero scrim">
        <h1 className="wordmark" lang="en">
          Sunn
        </h1>
        <p className="lead">
          <T hi="जो आप कहना चाहते हैं, वो सब समझें" en="speech that's hard to understand, made clear" />
        </p>
        <button type="button" className="primary" onClick={onStart}>
          <T hi="शुरू करें" en="get started" />
        </button>
      </section>

      <section className="about scrim" aria-labelledby="how">
        <h2 id="how">
          <T hi="यह कैसे काम करता है" en="how it works" />
        </h2>
        <ol className="steps">
          {STEPS.map((step) => (
            <li key={step.en}>
              <T hi={step.hi} en={step.en} />
            </li>
          ))}
        </ol>
        <p className="privacy">
          <T
            hi="आपकी रिकॉर्डिंग इसी कंप्यूटर पर रहती हैं और सिर्फ़ आपकी बोली पहचानने के लिए Gnani को भेजी जाती हैं।"
            en="your recordings stay on this computer and are sent to Gnani only to recognize your speech."
          />
        </p>
        <footer lang="en">built with Gnani Prisma and Gnani Timbre</footer>
      </section>
    </div>
  )
}
