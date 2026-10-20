import { BookOpen, Mic, RotateCcw, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { Alert, useGo } from './ui.jsx'

// Delete account shortcut retained for safety and account control
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
  const go = useGo()

  const [stats, setStats] = useState(null)
  const [phrases, setPhrases] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const isMounted = useRef(true)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [statsData, phrasesData] = await Promise.all([
        api.stats(),
        api.listPhrases().catch(() => []),
      ])
      if (isMounted.current) {
        setStats(statsData)
        setPhrases(phrasesData)
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err)
      }
    } finally {
      if (isMounted.current) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    isMounted.current = true
    loadData()
    return () => {
      isMounted.current = false
    }
  }, [])

  if (loading && !stats) {
    return (
      <section className="screen narrow">
        <p className="screen-status" role="status">
          {t('app.loading')}
        </p>
      </section>
    )
  }

  if (error && !stats) {
    return (
      <section className="screen narrow">
        <Alert error={error} />
        <div className="error-actions">
          <button type="button" className="pill-outline" onClick={loadData}>
            <RotateCcw size={16} aria-hidden="true" strokeWidth={1.5} />
            <span>{t('error.retry')}</span>
          </button>
        </div>
      </section>
    )
  }

  const hitRate = stats?.top1_hit_rate == null ? '-' : `${Math.round(stats.top1_hit_rate * 100)}%`
  const numbers = [
    { value: stats?.phrases ?? 0, key: 'progress.phrases' },
    { value: stats?.enroll_samples ?? 0, key: 'progress.teaching' },
    { value: stats?.recognitions ?? 0, key: 'progress.spoken' },
    { value: hitRate, key: 'progress.firstRight' },
  ]

  return (
    <section className="screen progress-screen">
      <header className="progress-header">
        <h1>{t('progress.title')}</h1>
        <p className="muted">{t('progress.subtitle')}</p>
      </header>

      <Alert error={error} />

      <dl className="numbers">
        {numbers.map((n) => (
          <div key={n.key}>
            <dt>{t(n.key)}</dt>
            <dd>{n.value}</dd>
          </div>
        ))}
      </dl>

      {stats?.recognitions === 0 && (
        <article className="progress-empty-card" aria-labelledby="empty-progress-title">
          <h2 id="empty-progress-title">{t('progress.nothing')}</h2>
          <p className="muted">{t('progress.guidancePhrases')}</p>
          <div className="empty-actions">
            <button
              type="button"
              className="pill-outline"
              onClick={() => go('/app/speak')}
            >
              <Mic size={16} aria-hidden="true" strokeWidth={1.5} />
              <span>{t('progress.goSpeak')}</span>
            </button>
            <button
              type="button"
              className="pill-outline"
              onClick={() => go('/app/phrases')}
            >
              <BookOpen size={16} aria-hidden="true" strokeWidth={1.5} />
              <span>{t('progress.goPhrases')}</span>
            </button>
          </div>
        </article>
      )}

      <DeleteAccount />
    </section>
  )
}
