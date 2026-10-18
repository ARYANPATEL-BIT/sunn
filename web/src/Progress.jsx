import { Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { Alert, useGo } from './ui.jsx'

// Delete the account: one tap opens a plain confirmation, a second one deletes.
function DeleteAccount() {
  const { t } = useLang()
  const { logout } = useAuth()
  const go = useGo()
  const [asking, setAsking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function remove() {
    setBusy(true)
    setError(null)
    try {
      await api.deleteAccount()
      await logout()
      go('/', { replace: true })
    } catch (e) {
      setError(e)
      setBusy(false)
    }
  }

  return (
    <section className="danger" aria-labelledby="your-data">
      <h2 id="your-data">{t('progress.deleteTitle')}</h2>
      {asking ? (
        <div className="stack" role="group" aria-labelledby="delete-warning">
          <p id="delete-warning">{t('progress.deleteConfirm')}</p>
          <Alert error={error} />
          <div className="actions">
            <button type="button" className="pill-outline" onClick={() => setAsking(false)} disabled={busy} autoFocus>
              {t('progress.deleteNo')}
            </button>
            <button type="button" className="pill-outline destructive" onClick={remove} disabled={busy}>
              <Trash2 aria-hidden="true" strokeWidth={1.5} />
              <span>{t(busy ? 'progress.deleting' : 'progress.deleteYes')}</span>
            </button>
          </div>
        </div>
      ) : (
        <button type="button" className="link" onClick={() => setAsking(true)}>
          {t('progress.delete')}
        </button>
      )}
    </section>
  )
}

export default function Progress() {
  const { t } = useLang()
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    setError(null)
    api.stats().then(setStats, setError)
  }
  useEffect(load, [])

  if (!stats) {
    return (
      <section className="screen narrow">
        <Alert error={error} />
        {error && (
          <button type="button" className="pill-outline" onClick={load}>
            {t('error.retry')}
          </button>
        )}
      </section>
    )
  }

  const hitRate = stats.top1_hit_rate === null ? '–' : `${Math.round(stats.top1_hit_rate * 100)}%`
  const numbers = [
    { value: stats.phrases, key: 'progress.phrases' },
    { value: stats.enroll_samples, key: 'progress.teaching' },
    { value: stats.recognitions, key: 'progress.spoken' },
    { value: hitRate, key: 'progress.firstRight' },
  ]

  return (
    <section className="screen">
      <h1>{t('progress.title')}</h1>
      <dl className="numbers">
        {numbers.map((n) => (
          <div key={n.key}>
            <dt>{t(n.key)}</dt>
            <dd>{n.value}</dd>
          </div>
        ))}
      </dl>
      {stats.recognitions === 0 && <p className="muted">{t('progress.nothing')}</p>}
      <DeleteAccount />
    </section>
  )
}
