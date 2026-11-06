import { BookOpen, ChevronRight, Mic, RotateCcw, Square, Trash2, Volume2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { Alert, ICON, Sheet, useGo } from './ui.jsx'

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
    <section className="group-wrap" aria-labelledby="your-data">
      <h2 className="title-2" id="your-data">
        {t('progress.deleteTitle')}
      </h2>
      <div className="group">
        <button type="button" className="row" onClick={() => setAsking(true)} aria-haspopup="dialog">
          <Trash2 className="row-icon" {...ICON} />
          <span className="row-title">{t('progress.delete')}</span>
        </button>
      </div>
      <Sheet open={asking} onClose={() => setAsking(false)} labelledBy="delete-warning">
        <div className="confirm">
          <p className="sheet-title" id="delete-warning">
            {t('progress.deleteConfirm')}
          </p>
          <Alert error={error} />
          <div className="actions stacked">
            <button type="button" className="button" onClick={() => setAsking(false)} disabled={busy} data-autofocus>
              {t('progress.deleteNo')}
            </button>
            <button type="button" className="button" onClick={remove} disabled={busy}>
              <Trash2 {...ICON} />
              <span>{t(busy ? 'progress.deleting' : 'progress.deleteYes')}</span>
            </button>
          </div>
        </div>
      </Sheet>
    </section>
  )
}

// Confirmed phrases per week, stacked: understood directly (full ink) under assisted (gray),
// a 2px gap between them, the total above each bar, a hairline grid. Values are in the table view.
function WeeklyChart({ weeks, lang }) {
  const { t } = useLang()
  const max = Math.max(1, ...weeks.map((w) => w.confirmed))
  const ticks = max > 1 ? [0, Math.round(max / 2), max] : [0, max]
  return (
    <figure className="chart" role="img" aria-label={t('progress.weeklyDesc')}>
      <div className="chart-plot" aria-hidden="true">
        {ticks.map((tick) => (
          <div key={tick} className="chart-gridline" style={{ '--at': tick / max }}>
            <span>{tick}</span>
          </div>
        ))}
        <div className="chart-columns">
          {weeks.map((w) => {
            const clear = Math.min(w.clear, w.confirmed)
            const assisted = Math.max(0, w.confirmed - w.clear)
            return (
              <div key={w.week_start} className="chart-column">
                <div className="chart-bar" style={{ '--h': w.confirmed / max }}>
                  {w.confirmed > 0 && <span className="chart-total">{w.confirmed}</span>}
                  {assisted > 0 && <span className="segment assisted" style={{ flexGrow: assisted }} />}
                  {clear > 0 && <span className="segment clear" style={{ flexGrow: clear }} />}
                </div>
                <span className="chart-x">{formatWeekStart(w.week_start, lang)}</span>
              </div>
            )
          })}
        </div>
      </div>
    </figure>
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
      const [statsData, phrasesData] = await Promise.all([api.stats(), api.listPhrases().catch(() => [])])
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
        <div className="actions">
          <button type="button" className="button" onClick={loadData}>
            <RotateCcw {...ICON} />
            <span>{t('error.retry')}</span>
          </button>
        </div>
      </section>
    )
  }

  const hitRate = stats?.top1_hit_rate == null ? '-' : `${Math.round(stats.top1_hit_rate * 100)}%`
  const urgentCount = phrases?.filter((p) => p.urgent).length ?? 0
  const weeks = stats?.clear_without_help_by_week ?? []
  const hasActivity = weeks.some((w) => w.confirmed > 0)
  const metrics = [
    ['progress.phrases', stats?.phrases ?? 0],
    ['progress.teaching', stats?.enroll_samples ?? 0],
    ['progress.spoken', stats?.recognitions ?? 0],
    ['progress.confirmed', stats?.confirmed ?? 0],
    ['progress.urgentPhrases', urgentCount],
  ]

  return (
    <section className="screen progress-screen">
      <h1 className="large-title">{t('progress.title')}</h1>

      <Alert error={error} />

      {stats?.recognitions === 0 && (
        <article className="status-card" aria-labelledby="empty-progress-title">
          <Mic className="status-icon" {...ICON} />
          <h2 id="empty-progress-title">{t('progress.nothing')}</h2>
          <p>{t('progress.guidancePhrases')}</p>
          <div className="actions">
            <button type="button" className="button" onClick={() => go('/app/speak')}>
              <Mic {...ICON} />
              <span>{t('progress.goSpeak')}</span>
            </button>
            <button type="button" className="button" onClick={() => go('/app/phrases')}>
              <BookOpen {...ICON} />
              <span>{t('progress.goPhrases')}</span>
            </button>
          </div>
        </article>
      )}

      {/* Overview: the big numbers */}
      <section className="progress-section" aria-labelledby="heading-overview">
        <h2 id="heading-overview" className="title-2">
          {t('progress.overviewHeading')}
        </h2>
        <div className="metrics">
          {metrics.map(([key, value]) => (
            <div className="metric-card" key={key}>
              <span className="metric-value">{value}</span>
              <span className="metric-label">{t(key)}</span>
            </div>
          ))}
        </div>
      </section>

      {/* How often the first suggestion was the one */}
      {Boolean(stats?.confirmed) && (
        <article className="progress-section match" aria-labelledby="heading-match-rate">
          <h2 id="heading-match-rate" className="title-2">
            {t('progress.firstRight')}
          </h2>
          <div className="match-card">
            <span className="match-value">{hitRate}</span>
            <div
              className="meter"
              role="progressbar"
              aria-valuenow={Math.round((stats?.top1_hit_rate ?? 0) * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={t('progress.firstRight')}
            >
              <div style={{ transform: `scaleX(${stats?.top1_hit_rate ?? 0})` }} />
            </div>
            <p className="match-detail">
              {stats?.top1_hits ?? 0} / {stats?.confirmed ?? 0} {t('progress.confirmed').toLowerCase()}
            </p>
            <p className="match-explain">{t('progress.matchRateExplanation')}</p>
          </div>
        </article>
      )}

      {/* Frequently Used Phrases */}
      <section className="progress-section" aria-labelledby="heading-top-phrases">
        <h2 id="heading-top-phrases" className="title-2">
          {t('progress.topPhrasesHeading')}
        </h2>
        {stats?.top_phrases && stats.top_phrases.length > 0 ? (
          <ul className="group" aria-label={t('progress.topPhrasesHeading')}>
            {stats.top_phrases.map((phrase, idx) => {
              const isPlaying = playingPhrase === phrase.text
              return (
                <li key={phrase.phrase_id} className="row top-phrase-item">
                  <span className="rank" aria-hidden="true">
                    {idx + 1}
                  </span>
                  <span className="row-text">
                    <span className="row-title" lang={user.language}>
                      {phrase.text}
                    </span>
                    <span className="row-sub">{t('progress.usesCount', { count: phrase.uses })}</span>
                  </span>
                  <button
                    type="button"
                    className="icon-button"
                    onClick={() => handlePlayPhrase(phrase.text)}
                    aria-label={`${t(isPlaying ? 'phrases.stopPlaying' : 'phrases.listen')}: ${phrase.text}`}
                  >
                    {isPlaying ? <Square fill="currentColor" {...ICON} /> : <Volume2 {...ICON} />}
                  </button>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="empty-note">{t('progress.topPhrasesEmpty')}</p>
        )}
      </section>

      {/* Weekly trend */}
      <section className="progress-section" aria-labelledby="heading-weekly">
        <div className="section-header-row">
          <div>
            <h2 id="heading-weekly" className="title-2">
              {t('progress.weeklyHeading')}
            </h2>
            <p className="section-sub">{t('progress.weeklyDesc')}</p>
          </div>
          {hasActivity && (
            <button
              type="button"
              className="button small"
              onClick={() => setShowTableView(!showTableView)}
              aria-expanded={showTableView}
            >
              <span>{t(showTableView ? 'progress.weeklyChartToggle' : 'progress.weeklyTableToggle')}</span>
            </button>
          )}
        </div>

        {hasActivity ? (
          <div className="chart-card">
            {showTableView ? (
              <table className="data-table">
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
            ) : (
              <>
                <div className="chart-legend" aria-hidden="true">
                  <span className="legend-item">
                    <span className="swatch clear" />
                    <span>{t('progress.weeklyClearLabel')}</span>
                  </span>
                  <span className="legend-item">
                    <span className="swatch assisted" />
                    <span>{t('progress.weeklyAssistedLabel')}</span>
                  </span>
                </div>
                <WeeklyChart weeks={weeks} lang={lang} />
              </>
            )}
          </div>
        ) : (
          <p className="empty-note">{t('progress.noActivity')}</p>
        )}
      </section>

      {/* Supportive suggestions */}
      <section className="group-wrap" aria-labelledby="heading-guidance">
        <h2 id="heading-guidance" className="title-2">
          {t('progress.guidanceHeading')}
        </h2>
        <div className="group">
          <button type="button" className="row" onClick={() => go('/app/phrases')}>
            <BookOpen className="row-icon" {...ICON} />
            <span className="row-text">
              <span className="row-title">{t('progress.goPhrases')}</span>
              <span className="row-sub">{t('progress.guidancePhrases')}</span>
            </span>
            <ChevronRight className="row-chevron" {...ICON} />
          </button>
          <button type="button" className="row" onClick={() => go('/app/enroll')}>
            <Mic className="row-icon" {...ICON} />
            <span className="row-text">
              <span className="row-title">{t('progress.goTeach')}</span>
              <span className="row-sub">{t('progress.guidanceEnroll')}</span>
            </span>
            <ChevronRight className="row-chevron" {...ICON} />
          </button>
        </div>
      </section>

      <DeleteAccount />

      {/* What the numbers are, and aren't */}
      <aside className="footnote" aria-labelledby="heading-disclaimer">
        <h3 id="heading-disclaimer">{t('progress.disclaimerHeading')}</h3>
        <p>{t('progress.disclaimerText')}</p>
      </aside>
    </section>
  )
}
