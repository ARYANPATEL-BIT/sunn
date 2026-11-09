import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import * as api from '../api.js'
import { useAuth } from '../auth.jsx'
import { useLang } from '../i18n/index.jsx'
import { Alert, Icon, PrimaryButton, reducedMotion } from '../ui/index.js'
import { HonestNote } from './HonestNote.jsx'
import { TrainingsNav } from './TrainingsNav.jsx'

const LESSON_ROUTES = {
  'easy-starts-1': '/trainings/smooth-speaking/easy-starts/easy-starts-1',
  'easy-starts-2': '/trainings/smooth-speaking/easy-starts/easy-starts-2',
  'easy-starts-3': '/trainings/smooth-speaking/easy-starts/easy-starts-3',
  'easy-starts-4': '/trainings/smooth-speaking/easy-starts/easy-starts-4',
  's-and-sh-1': '/trainings/clear-sounds/s-and-sh/s-and-sh-1',
  's-and-sh-2': '/trainings/clear-sounds/s-and-sh/s-and-sh-2',
  's-and-sh-3': '/trainings/clear-sounds/s-and-sh/s-and-sh-3',
  's-and-sh-4': '/trainings/clear-sounds/s-and-sh/s-and-sh-4',
  'sound-play-1': '/trainings/kids-speaking/sound-play/sound-play-1',
  'sound-play-2': '/trainings/kids-speaking/sound-play/sound-play-2',
  'sound-play-3': '/trainings/kids-speaking/sound-play/sound-play-3',
  'sound-play-4': '/trainings/kids-speaking/sound-play/sound-play-4',
  'introductions-1': '/trainings/everyday-talk/introductions/introductions-1',
  'introductions-2': '/trainings/everyday-talk/introductions/introductions-2',
  'introductions-3': '/trainings/everyday-talk/introductions/introductions-3',
  'introductions-4': '/trainings/everyday-talk/introductions/introductions-4',
}

export function TrainingsHome() {
  const { user } = useAuth()
  const { t, lang } = useLang()
  const navigate = useNavigate()
  const [categories, setCategories] = useState([])
  const [progress, setProgress] = useState(null)
  const [resumeCourse, setResumeCourse] = useState(null)
  const [trickySounds, setTrickySounds] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const cats = await api.listTrainingsCategories()
      setCategories(cats)

      if (user) {
        const [prog, tricky] = await Promise.all([
          api.getTrainingsProgress(),
          api.getTrickySounds().catch(() => []),
        ])
        setProgress(prog)
        setTrickySounds(Array.isArray(tricky) ? tricky : [])

        if (prog?.resume?.course_id) {
          try {
            const course = await api.getTrainingsCourse(prog.resume.course_id)
            setResumeCourse(course)
          } catch {
            // Non-fatal if resume course detail fails
          }
        }
      } else {
        setProgress(null)
        setResumeCourse(null)
        setTrickySounds([])
      }
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [user])

  const resumeLesson = resumeCourse?.lessons?.find((l) => l.id === progress?.resume?.lesson_id)
  const resumeCategory = resumeCourse?.category_id || categories[0]?.id

  const handlePractiseSound = async (lessonId) => {
    if (!lessonId) return
    const route = LESSON_ROUTES[lessonId]
    if (route) {
      navigate(route, { viewTransition: !reducedMotion() })
      return
    }
    try {
      const lesson = await api.getTrainingsLesson(lessonId)
      if (lesson?.category_id && lesson?.course_id) {
        navigate(`/trainings/${lesson.category_id}/${lesson.course_id}/${lesson.id}`, {
          viewTransition: !reducedMotion(),
        })
      }
    } catch {
      // Non-blocking
    }
  }

  return (
    <div className={`trainings-page ${user ? 'with-tabs' : ''}`}>
      <TrainingsNav />

      <main className="trainings-content" id="trainings-main">
        <header className="trainings-header">
          <h1 className="display trainings-title">{t('trainings.homeTitle')}</h1>
          <p className="lede trainings-subtitle">{t('trainings.homeSubtitle')}</p>
        </header>

        {loading && (
          <div className="trainings-skeletons" aria-busy="true" aria-label={t('app.loading')}>
            <div className="skeleton-card" />
            <div className="skeleton-card" />
            <div className="skeleton-card" />
            <div className="skeleton-card" />
          </div>
        )}

        {error && (
          <div className="trainings-error">
            <Alert error={error} />
            <button type="button" className="button" onClick={loadData}>
              {t('trainings.retry')}
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            {user && progress?.resume && resumeCourse && (
              <section className="trainings-resume-section" aria-labelledby="resume-title">
                <div className="resume-card">
                  <div className="resume-info">
                    <span className="resume-kicker" id="resume-title">
                      {t('trainings.continueTitle')}
                    </span>
                    <h2 className="resume-course-title">{resumeCourse.title[lang] || resumeCourse.title.en}</h2>
                    {resumeLesson && (
                      <p className="resume-lesson-title">
                        {resumeLesson.title[lang] || resumeLesson.title.en}
                      </p>
                    )}
                    {resumeCourse.percent != null && (
                      <div className="trainings-progress-wrap">
                        <div
                          className="trainings-progress-bar"
                          role="progressbar"
                          aria-valuenow={resumeCourse.percent}
                          aria-valuemin={0}
                          aria-valuemax={100}
                        >
                          <div
                            className="trainings-progress-fill"
                            style={{ width: `${resumeCourse.percent}%` }}
                          />
                        </div>
                        <span className="trainings-progress-label">
                          {t('trainings.progressPercent', { percent: resumeCourse.percent })}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="resume-action">
                    <Link
                      to={`/trainings/${resumeCategory}/${progress.resume.course_id}/${progress.resume.lesson_id}`}
                      className="button primary"
                      viewTransition={!reducedMotion()}
                    >
                      {t('trainings.continueAction')}
                    </Link>
                  </div>
                </div>
              </section>
            )}

            <section className="trainings-grid-section" aria-label={t('trainings.homeTitle')}>
              <div className="trainings-grid">
                {categories.map((category) => {
                  const title = category.title[lang] || category.title.en
                  const subtitle = category.subtitle[lang] || category.subtitle.en
                  const courseCountText = t(
                    category.course_count === 1 ? 'trainings.singleCourse' : 'trainings.coursesCount',
                    { count: category.course_count },
                  )

                  return (
                    <Link
                      key={category.id}
                      to={`/trainings/${category.id}`}
                      className="category-card"
                      viewTransition={!reducedMotion()}
                    >
                      <div className="category-header">
                        <div className="category-icon-seat" aria-hidden="true">
                          <Icon name={category.icon} className="category-icon" />
                        </div>
                        {category.audience === 'kids' && (
                          <span className="category-adult-badge">{t('trainings.withAdult')}</span>
                        )}
                      </div>
                      <div className="category-body">
                        <h2 className="category-title">{title}</h2>
                        <p className="category-subtitle">{subtitle}</p>
                      </div>
                      <div className="category-footer">
                        <span className="category-courses-count">{courseCountText}</span>
                        {category.percent != null && (
                          <span className="category-progress-pill">
                            {t('trainings.progressPercent', { percent: category.percent })}
                          </span>
                        )}
                      </div>
                    </Link>
                  )
                })}
              </div>
            </section>

            {user && (
              <section className="trainings-personalized-section" aria-label={t('trainings.trickySoundsTitle')}>
                {/* 1. Your Tricky Sounds Card */}
                <article className="personalized-card tricky-sounds-card">
                  <div className="personalized-card-header">
                    <span className="personalized-kicker">{t('trainings.trickySoundsSubtitle')}</span>
                    <h2 className="personalized-card-title">{t('trainings.trickySoundsTitle')}</h2>
                  </div>

                  {trickySounds.length === 0 ? (
                    <p className="personalized-empty-text">{t('trainings.trickySoundsEmpty')}</p>
                  ) : (
                    <div className="tricky-sounds-list">
                      {trickySounds.slice(0, 3).map((sound) => {
                        const label = sound.label?.[lang] || sound.label?.en || sound.sound_id
                        const reasonKey = `trainings.why_${sound.why_key}`

                        return (
                          <div key={sound.sound_id} className="tricky-sound-row">
                            <div className="sound-badge-seat">
                              <span className="sound-badge" lang="hi">{label}</span>
                            </div>
                            <div className="sound-info">
                              <p className="sound-reason">{t(reasonKey)}</p>
                            </div>
                            {sound.practise_lesson_id && (
                              <button
                                type="button"
                                className="button small practise-sound-btn"
                                onClick={() => handlePractiseSound(sound.practise_lesson_id)}
                              >
                                {t('trainings.practiseSound')}
                              </button>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </article>

                {/* 2. Easier Ways To Say It Card */}
                <article className="personalized-card easier-ways-card">
                  <div className="personalized-card-header">
                    <span className="personalized-kicker">{t('trainings.easierWaysTitle')}</span>
                    <h2 className="personalized-card-title">{t('trainings.easierWaysTitle')}</h2>
                  </div>
                  <p className="personalized-card-desc">{t('trainings.easierWaysDesc')}</p>
                  <div className="personalized-card-action">
                    <Link
                      to="/trainings/easier-ways"
                      className="button primary open-easier-ways-btn"
                      viewTransition={!reducedMotion()}
                    >
                      <Icon name="idea" />
                      <span>{t('trainings.openEasierWays')}</span>
                    </Link>
                  </div>
                </article>
              </section>
            )}
          </>
        )}

        <HonestNote />
      </main>
    </div>
  )
}
