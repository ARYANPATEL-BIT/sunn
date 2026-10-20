import { BookOpen, Mic, RotateCcw, Square, Trash2, Volume2 } from 'lucide-react'
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
  const [playingPhrase, setPlayingPhrase] = useState(null)
  const isMounted = useRef(true)

  const handlePlayPhrase = async (text) => {
    if (playingPhrase === text) {
      api.stopAudio()
      setPlayingPhrase(null)
      return
    }
    setPlayingPhrase(text)
    try {
      await api.say(text)
    } catch {
      // Audio errors non-blocking on progress screen
    } finally {
      if (isMounted.current) setPlayingPhrase(null)
    }
  }

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
      api.stopAudio()
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
  const urgentCount = phrases?.filter((p) => p.urgent).length ?? 0

  return (
    <section className="screen progress-screen">
      <header className="progress-header">
        <h1>{t('progress.title')}</h1>
        <p className="muted">{t('progress.subtitle')}</p>
      </header>

      <Alert error={error} />

      {/* Section 1: Overview Metrics */}
      <section className="progress-section" aria-labelledby="heading-overview">
        <h2 id="heading-overview">{t('progress.overviewHeading')}</h2>
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">{t('progress.phrases')}</span>
            <span className="metric-value">{stats?.phrases ?? 0}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">{t('progress.teaching')}</span>
            <span className="metric-value">{stats?.enroll_samples ?? 0}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">{t('progress.spoken')}</span>
            <span className="metric-value">{stats?.recognitions ?? 0}</span>
          </div>
          <div className="metric-card">
            <span className="metric-label">{t('progress.confirmed')}</span>
            <span className="metric-value">{stats?.confirmed ?? 0}</span>
          </div>
          <div className="metric-card urgent-metric">
            <span className="metric-label">{t('progress.urgentPhrases')}</span>
            <span className="metric-value">{urgentCount}</span>
          </div>
        </div>
      </section>

      {/* Section 2: Suggestion Match Rate */}
      {Boolean(stats?.confirmed) && (
        <article className="match-rate-card" aria-labelledby="heading-match-rate">
          <div className="match-rate-header">
            <h2 id="heading-match-rate">{t('progress.matchRateHeading')}</h2>
            <span className="match-rate-percent">{hitRate}</span>
          </div>
          <p className="muted">{t('progress.matchRateExplanation')}</p>
          <div
            className="match-rate-bar"
            role="progressbar"
            aria-valuenow={Math.round((stats?.top1_hit_rate ?? 0) * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={t('progress.matchRateHeading')}
          >
            <div
              className="match-rate-fill"
              style={{ width: `${Math.round((stats?.top1_hit_rate ?? 0) * 100)}%` }}
            />
          </div>
          <small className="muted hit-detail">
            {stats?.top1_hits ?? 0} / {stats?.confirmed ?? 0} {t('progress.confirmed').toLowerCase()}
          </small>
        </article>
      )}

      {/* Section 3: Frequently Used Phrases */}
      <section className="progress-section" aria-labelledby="heading-top-phrases">
        <h2 id="heading-top-phrases">{t('progress.topPhrasesHeading')}</h2>
        {stats?.top_phrases && stats.top_phrases.length > 0 ? (
          <ul className="top-phrases-list" aria-label={t('progress.topPhrasesHeading')}>
            {stats.top_phrases.map((phrase, idx) => {
              const isPlaying = playingPhrase === phrase.text
              return (
                <li key={phrase.phrase_id} className="top-phrase-item">
                  <div className="top-phrase-main">
                    <span className="rank-badge" aria-hidden="true">
                      {idx + 1}
                    </span>
                    <span className="phrase-text">{phrase.text}</span>
                  </div>
                  <div className="top-phrase-meta">
                    <span className="uses-badge">
                      {t('progress.usesCount', { count: phrase.uses })}
                    </span>
                    <button
                      type="button"
                      className="icon-pill-btn"
                      onClick={() => handlePlayPhrase(phrase.text)}
                      aria-label={`${t(isPlaying ? 'phrases.stopPlaying' : 'phrases.listen')}: ${phrase.text}`}
                    >
                      {isPlaying ? (
                        <Square size={15} fill="currentColor" aria-hidden="true" />
                      ) : (
                        <Volume2 size={15} aria-hidden="true" strokeWidth={1.5} />
                      )}
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="muted empty-note">{t('progress.topPhrasesEmpty')}</p>
        )}
      </section>

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
