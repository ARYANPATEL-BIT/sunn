import { useEffect, useState } from 'react'
import * as api from './api.js'
import { Alert, T } from './ui.jsx'

export default function Progress({ userId }) {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    setError(null)
    api.stats(userId).then(setStats, setError)
  }
  useEffect(load, [userId])

  if (!stats) {
    return (
      <section className="screen narrow">
        <Alert error={error} />
        {error && (
          <button type="button" className="secondary" onClick={load}>
            <T hi="फिर से कोशिश करें" en="try again" />
          </button>
        )}
      </section>
    )
  }

  const hitRate = stats.top1_hit_rate === null ? '–' : `${Math.round(stats.top1_hit_rate * 100)}%`
  const numbers = [
    { value: stats.phrases, hi: 'वाक्य', en: 'phrases' },
    { value: stats.enroll_samples, hi: 'सिखाने की रिकॉर्डिंग', en: 'teaching recordings' },
    { value: stats.recognitions, hi: 'बार बोला', en: 'times spoken' },
    { value: hitRate, hi: 'पहला अनुमान सही', en: 'first guess right' },
  ]

  return (
    <section className="screen">
      <h1>
        <T hi="प्रगति" en="progress" />
      </h1>
      <dl className="numbers">
        {numbers.map((n) => (
          <div key={n.en}>
            <dt>
              <T hi={n.hi} en={n.en} />
            </dt>
            <dd lang="en">{n.value}</dd>
          </div>
        ))}
      </dl>
      {stats.recognitions === 0 && (
        <p className="hint">
          <T
            hi="अभी तक कुछ नहीं बोला गया। बोलें में सूरज दबाकर शुरू करें।"
            en="nothing spoken yet. tap the sun in speak to start."
          />
        </p>
      )}
    </section>
  )
}
