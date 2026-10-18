import { useEffect, useState } from 'react'
import * as api from './api.js'
import { Alert, T } from './ui.jsx'

export default function Progress({ userId }) {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.stats(userId).then(setStats, setError)
  }, [userId])

  if (!stats) return <Alert error={error} />

  const hitRate = stats.top1_hit_rate === null ? '—' : `${Math.round(stats.top1_hit_rate * 100)}%`
  const cards = [
    { value: stats.phrases, hi: 'वाक्य', en: 'Phrases' },
    { value: stats.enroll_samples, hi: 'सिखाने की रिकॉर्डिंग', en: 'Enroll recordings' },
    { value: stats.recognitions, hi: 'बार बोला', en: 'Recognitions' },
    { value: hitRate, hi: 'पहला अनुमान सही', en: 'Top guess right' },
  ]

  return (
    <section className="cards">
      {cards.map((card) => (
        <div key={card.en} className="card">
          <span className="value">{card.value}</span>
          <T hi={card.hi} en={card.en} />
        </div>
      ))}
    </section>
  )
}
