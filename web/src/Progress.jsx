import { BookOpen, Mic, RotateCcw, Square, Trash2, Volume2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { Alert, useGo } from './ui.jsx'

function formatWeekStart(isoDate, currentLang) {
  try {
    const d = new Date(isoDate)
    return d.toLocaleDateString(currentLang === 'hi' ? 'hi-IN' : 'en-US', {
      day: 'numeric',
      month: 'short',
    })
  } catch {
    return isoDate
  }
}

// Delete account shortcut retained for safety and account control
function DeleteAccount() {
  const { t } = useLang()
  const { deleteAccount } = useAuth()
  const [asking, setAsking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function remove() {
    setBusy(true)
    setError(null)
    try {
      await deleteAccount() // signs out, and /app/* then goes home
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
  const { lang, t } = useLang()
  const { user } = useAuth()
  const go = useGo()

  const [stats, setStats] = useState(null)
  const [phrases, setPhrases] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [playingPhrase, setPlayingPhrase] = useState(null)
  const [showTableView, setShowTableView] = useState(false)
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
  const weeks = stats?.clear_without_help_by_week ?? []
  const maxWeekly = Math.max(1, ...weeks.map((w) => w.confirmed))

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
            <h2 id="heading-match-rate">{t('progress.firstRight')}</h2>
            <span className="match-rate-percent">{hitRate}</span>
          </div>
          <p className="muted">{t('progress.matchRateExplanation')}</p>
          <div
            className="match-rate-bar"
            role="progressbar"
            aria-valuenow={Math.round((stats?.top1_hit_rate ?? 0) * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={t('progress.firstRight')}
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
                    <span className="phrase-text" lang={user.language}>
                      {phrase.text}
                    </span>
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

      {/* Section 4: Weekly Activity Trend Chart */}
      <section className="progress-section" aria-labelledby="heading-weekly">
        <div className="section-header-row">
          <div>
            <h2 id="heading-weekly">{t('progress.weeklyHeading')}</h2>
            <p className="muted">{t('progress.weeklyDesc')}</p>
          </div>
          {weeks.some((w) => w.confirmed > 0) && (
            <button
              type="button"
              className="pill-outline table-toggle-btn"
              onClick={() => setShowTableView(!showTableView)}
              aria-expanded={showTableView}
            >
              <span>{t(showTableView ? 'progress.weeklyChartToggle' : 'progress.weeklyTableToggle')}</span>
            </button>
          )}
        </div>

        {weeks.some((w) => w.confirmed > 0) ? (
          <div className="weekly-chart-card">
            {showTableView ? (
              <div className="chart-table-container">
                <table className="accessible-chart-table">
                  <caption className="visually-hidden">{t('progress.weeklyDesc')}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{t('progress.weekColumn')}</th>
                      <th scope="col">{t('progress.confirmed')}</th>
                      <th scope="col">{t('progress.weeklyClearLabel')}</th>
                      <th scope="col">{t('progress.weeklyAssistedLabel')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {weeks.map((w) => (
                      <tr key={w.week_start}>
                        <th scope="row">{formatWeekStart(w.week_start, lang)}</th>
                        <td>{w.confirmed}</td>
                        <td>{w.clear}</td>
                        <td>{Math.max(0, w.confirmed - w.clear)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <>
                <div className="chart-legend" aria-hidden="true">
                  <span className="legend-item">
                    <span className="legend-dot assisted" />
                    <span>{t('progress.weeklyAssistedLabel')}</span>
                  </span>
                  <span className="legend-item">
                    <span className="legend-dot clear" />
                    <span>{t('progress.weeklyClearLabel')}</span>
                  </span>
                </div>

                <div className="svg-chart-container" role="img" aria-label={t('progress.weeklyDesc')}>
                  <svg viewBox="0 0 400 160" className="activity-svg" preserveAspectRatio="none">
                    <line x1="10" y1="130" x2="390" y2="130" stroke="var(--line)" strokeWidth="1" />
                    {weeks.map((w, idx) => {
                      const x = 20 + idx * 46
                      const barWidth = 28
                      const maxH = 100
                      const total = w.confirmed
                      const h = total > 0 ? Math.max(8, (total / maxWeekly) * maxH) : 0
                      const y = 130 - h
                      const clearH = total > 0 ? (w.clear / total) * h : 0
                      const assistedH = h - clearH

                      return (
                        <g key={w.week_start} className="chart-bar-group">
                          {total > 0 ? (
                            <>
                              {assistedH > 0 && (
                                <rect
                                  x={x}
                                  y={y}
                                  width={barWidth}
                                  height={assistedH}
                                  rx="3"
                                  fill="var(--saffron)"
                                  opacity="0.9"
                                />
                              )}
                              {clearH > 0 && (
                                <rect
                                  x={x}
                                  y={y + assistedH}
                                  width={barWidth}
                                  height={clearH}
                                  rx="3"
                                  fill="var(--haze)"
                                  opacity="0.8"
                                />
                              )}
                            </>
                          ) : (
                            <circle cx={x + barWidth / 2} cy={130} r="2" fill="var(--line-strong)" />
                          )}
                          <text
                            x={x + barWidth / 2}
                            y="148"
                            textAnchor="middle"
                            fontSize="10"
                            fill="var(--mist)"
                          >
                            {formatWeekStart(w.week_start, lang)}
                          </text>
                        </g>
                      )
                    })}
                  </svg>
                </div>
              </>
            )}
          </div>
        ) : (
          <p className="muted empty-note">{t('progress.noActivity')}</p>
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

      {/* Section 5: Supportive Suggestions and Quick Links */}
      <section className="progress-section" aria-labelledby="heading-guidance">
        <h2 id="heading-guidance">{t('progress.guidanceHeading')}</h2>
        <div className="guidance-grid">
          <div className="guidance-item">
            <p>{t('progress.guidancePhrases')}</p>
            <button
              type="button"
              className="pill-outline"
              onClick={() => go('/app/phrases')}
            >
              <BookOpen size={16} aria-hidden="true" strokeWidth={1.5} />
              <span>{t('progress.goPhrases')}</span>
            </button>
          </div>
          <div className="guidance-item">
            <p>{t('progress.guidanceEnroll')}</p>
            <button
              type="button"
              className="pill-outline"
              onClick={() => go('/app/enroll')}
            >
              <Mic size={16} aria-hidden="true" strokeWidth={1.5} />
              <span>{t('progress.goTeach')}</span>
            </button>
          </div>
        </div>
      </section>

      {/* Section 6: Statistical Disclaimer and Transparency */}
      <aside className="disclaimer-card" aria-labelledby="heading-disclaimer">
        <h3 id="heading-disclaimer">{t('progress.disclaimerHeading')}</h3>
        <p className="muted">{t('progress.disclaimerText')}</p>
      </aside>

      <DeleteAccount />
    </section>
  )
}
