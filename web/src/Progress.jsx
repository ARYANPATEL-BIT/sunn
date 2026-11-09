import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { Alert, Button, Icon, Sheet, useGo } from './ui/index.js'

const COURSE_METADATA = {
  'easy-starts': {
    title: { en: 'Easy starts', hi: 'आराम से शुरुआत' },
    categoryId: 'smooth-speaking',
  },
  's-and-sh': {
    title: { en: 'S and Sh', hi: 'स और श' },
    categoryId: 'clear-sounds',
  },
  introductions: {
    title: { en: 'Introductions', hi: 'परिचय' },
    categoryId: 'everyday-talk',
  },
  'sound-play': {
    title: { en: 'Fun with sounds', hi: 'आवाज़ों से खेल' },
    categoryId: 'kids-speaking',
  },
}

const WEEK_DAYS = [
  'progress.dayM',
  'progress.dayT',
  'progress.dayW',
  'progress.dayTh',
  'progress.dayF',
  'progress.daySa',
  'progress.daySu',
]

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
          <Icon name="trash" className="row-icon" />
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
            <Button onClick={() => setAsking(false)} disabled={busy} data-autofocus>
              {t('progress.deleteNo')}
            </Button>
            <Button icon="trash" onClick={remove} disabled={busy}>
              {t(busy ? 'progress.deleting' : 'progress.deleteYes')}
            </Button>
          </div>
        </div>
      </Sheet>
    </section>
  )
}

// Confirmed phrases per week, stacked: understood directly (solid ink) under assisted (an ink
// outline), so the two differ by shape, not color. The total in mono above each bar, a hairline
// grid. Values are also in the table view.
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
  const [trainingsProgress, setTrainingsProgress] = useState(null)
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
      const [statsData, phrasesData, progData] = await Promise.all([
        api.stats(),
        api.listPhrases().catch(() => []),
        api.getTrainingsProgress().catch(() => null),
      ])
      if (isMounted.current) {
        setStats(statsData)
        setPhrases(phrasesData)
        setTrainingsProgress(progData)
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
          <Button icon="rotate" onClick={loadData}>
            {t('error.retry')}
          </Button>
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
          <Icon name="mic" className="status-icon" />
          <h2 id="empty-progress-title">{t('progress.nothing')}</h2>
          <p>{t('progress.guidancePhrases')}</p>
          <div className="actions">
            <Button icon="mic" onClick={() => go('/app/speak')}>
              {t('progress.goSpeak')}
            </Button>
            <Button icon="book" onClick={() => go('/app/phrases')}>
              {t('progress.goPhrases')}
            </Button>
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
                    {String(idx + 1).padStart(2, '0')}
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
                    <Icon name={isPlaying ? 'stop' : 'volume'} />
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

      {/* Trainings Section */}
      <section className="progress-section trainings-progress-section" aria-labelledby="heading-trainings">
        <div className="section-header-row">
          <div>
            <h2 id="heading-trainings" className="title-2">
              {t('progress.trainingsHeading')}
            </h2>
            <p className="section-sub">{t('progress.trainingsDesc')}</p>
          </div>
        </div>

        {/* Trainings overview numbers */}
        <div className="metrics">
          <div className="metric-card">
            <span className="metric-value">{trainingsProgress?.lessons_done ?? 0}</span>
            <span className="metric-label">{t('progress.lessonsDone')}</span>
          </div>
          <div className="metric-card">
            <span className="metric-value">{trainingsProgress?.minutes_practised ?? 0}</span>
            <span className="metric-label">{t('progress.minutesPractised')}</span>
          </div>
        </div>

        {/* Days practised this week: 7 simple squares with a check, not dots */}
        <div className="trainings-days-block">
          <span className="days-block-title">{t('progress.daysThisWeek')}</span>
          <div className="days-practised-grid" role="group" aria-label={t('progress.daysThisWeek')}>
            {WEEK_DAYS.map((dayKey, idx) => {
              const daysCount = trainingsProgress?.days_this_week ?? 0
              const isDone = idx < daysCount
              return (
                <div key={idx} className={`day-square-box ${isDone ? 'done' : ''}`}>
                  <div className="day-square" aria-hidden="true">
                    {isDone && <Icon name="check" className="day-check-icon" />}
                  </div>
                  <span className="day-label">{t(dayKey)}</span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Courses in progress */}
        <div className="trainings-courses-block">
          <h3 className="courses-block-title">{t('progress.coursesInProgress')}</h3>
          {trainingsProgress?.courses && trainingsProgress.courses.length > 0 ? (
            <div className="trainings-courses-list">
              {trainingsProgress.courses.map((c) => {
                const meta = COURSE_METADATA[c.id] || {}
                const courseTitle = meta.title?.[lang] || meta.title?.en || c.id
                const catId = meta.categoryId || 'smooth-speaking'
                return (
                  <div key={c.id} className="course-progress-card">
                    <div className="course-progress-header">
                      <span className="course-progress-name">{courseTitle}</span>
                      <span className="course-progress-percent">{c.percent}%</span>
                    </div>
                    <div
                      className="meter"
                      role="progressbar"
                      aria-valuenow={c.percent}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${courseTitle}: ${c.percent}%`}
                    >
                      <div style={{ transform: `scaleX(${c.percent / 100})` }} />
                    </div>
                    <div className="course-progress-action">
                      <button
                        type="button"
                        className="button small"
                        onClick={() => go(`/trainings/${catId}/${c.id}`)}
                      >
                        {t('progress.continueCourse')}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="trainings-empty-box">
              <p className="empty-note">{t('progress.noTrainingsYet')}</p>
              <Button onClick={() => go('/trainings')}>
                {t('progress.exploreTrainings')}
              </Button>
            </div>
          )}
        </div>
      </section>

      {/* Supportive suggestions */}
      <section className="group-wrap" aria-labelledby="heading-guidance">
        <h2 id="heading-guidance" className="title-2">
          {t('progress.guidanceHeading')}
        </h2>
        <div className="group">
          <button type="button" className="row" onClick={() => go('/app/phrases')}>
            <Icon name="book" className="row-icon" />
            <span className="row-text">
              <span className="row-title">{t('progress.goPhrases')}</span>
              <span className="row-sub">{t('progress.guidancePhrases')}</span>
            </span>
            <Icon name="chevronRight" className="row-chevron" />
          </button>
          <button type="button" className="row" onClick={() => go('/app/enroll')}>
            <Icon name="mic" className="row-icon" />
            <span className="row-text">
              <span className="row-title">{t('progress.goTeach')}</span>
              <span className="row-sub">{t('progress.guidanceEnroll')}</span>
            </span>
            <Icon name="chevronRight" className="row-chevron" />
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
