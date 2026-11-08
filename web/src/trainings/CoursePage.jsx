import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import * as api from '../api.js'
import { loginPath, useAuth } from '../auth.jsx'
import { useLang } from '../i18n/index.jsx'
import { Alert, Icon, PrimaryButton, reducedMotion } from '../ui/index.js'
import { HonestNote } from './HonestNote.jsx'
import { TrainingsNav } from './TrainingsNav.jsx'

export function CoursePage() {
  const { categoryId, courseId } = useParams()
  const { user } = useAuth()
  const { t, lang } = useLang()
  const navigate = useNavigate()
  const location = useLocation()

  const [course, setCourse] = useState(null)
  const [category, setCategory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [practiceNotice, setPracticeNotice] = useState(false)

  const loadCourse = async () => {
    setLoading(true)
    setError(null)
    try {
      const [courseData, catData] = await Promise.all([
        api.getTrainingsCourse(courseId),
        api.getTrainingsCategory(categoryId).catch(() => null),
      ])
      setCourse(courseData)
      setCategory(catData)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCourse()
  }, [courseId, categoryId, user])

  const title = course?.title?.[lang] || course?.title?.en || ''
  const summary = course?.summary?.[lang] || course?.summary?.en || ''
  const whatYouPractise =
    course?.what_you_practise?.[lang] || course?.what_you_practise?.en || []
  const categoryTitle = category?.title?.[lang] || category?.title?.en || ''

  const nextIncompleteIndex = course?.lessons?.findIndex((l) => !l.completed) ?? 0
  const nextIndex = nextIncompleteIndex === -1 ? 0 : nextIncompleteIndex
  const hasStarted = course?.lessons?.some((l) => l.completed) ?? false
  const buttonLabel = hasStarted
    ? t('trainings.continueLesson', { number: nextIndex + 1 })
    : t('trainings.startCourse')

  const handleStartPractice = (targetIndex = nextIndex) => {
    if (!user) {
      navigate(loginPath(location.pathname))
      return
    }
    const targetLesson = course?.lessons?.[targetIndex]
    if (targetLesson) {
      navigate(`/trainings/${categoryId}/${courseId}/${targetLesson.id}`, {
        viewTransition: !reducedMotion(),
      })
    }
  }

  return (
    <div className={`trainings-page ${user ? 'with-tabs' : ''}`}>
      <TrainingsNav
        backTo={`/trainings/${categoryId}`}
        backLabel={categoryTitle ? t('trainings.backToCategory', { category: categoryTitle }) : t('trainings.backToTrainings')}
      />

      <main className="trainings-content" id="course-main">
        {loading && (
          <div className="trainings-skeletons" aria-busy="true" aria-label={t('app.loading')}>
            <div className="skeleton-line title" />
            <div className="skeleton-line lede" />
            <div className="course-layout-skeleton">
              <div className="skeleton-card" />
              <div className="skeleton-card" />
            </div>
          </div>
        )}

        {error && (
          <div className="trainings-error">
            <Alert error={error} />
            <button type="button" className="button" onClick={loadCourse}>
              {t('trainings.retry')}
            </button>
          </div>
        )}

        {!loading && !error && course && (
          <>
            <div className="course-layout">
              {/* Left Column: Lesson list */}
              <section className="course-lessons-column" aria-label={t('trainings.courseContent')}>
                <div className="course-lessons-header">
                  <h2 className="course-lessons-heading">{t('trainings.courseContent')}</h2>
                  <span className="course-lessons-count-meta">
                    {t(course.lessons.length === 1 ? 'trainings.singleLesson' : 'trainings.lessonsCount', {
                      count: course.lessons.length,
                    })}
                  </span>
                </div>

                <ol className="lessons-list">
                  {course.lessons.map((lesson, idx) => {
                    const lessonTitle = lesson.title[lang] || lesson.title.en
                    const isNext = idx === nextIndex
                    const isCompleted = lesson.completed

                    return (
                      <li
                        key={lesson.id}
                        className={`lesson-row ${isNext ? 'is-next' : ''} ${isCompleted ? 'is-completed' : ''}`}
                        onClick={() => handleStartPractice(idx)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleStartPractice(idx)
                        }}
                      >
                        <div className="lesson-row-left">
                          <span className="lesson-num" aria-hidden="true">
                            {String(idx + 1).padStart(2, '0')}
                          </span>
                          <div className="lesson-row-info">
                            <span className="lesson-row-title">{lessonTitle}</span>
                            <div className="lesson-row-meta">
                              <span className="lesson-row-minutes">
                                {t('trainings.minutesCount', { count: lesson.minutes })}
                              </span>
                              <span className="lesson-meta-sep" aria-hidden="true">
                                ·
                              </span>
                              <span className="lesson-row-steps">
                                {t('trainings.stepCount', { count: lesson.step_count })}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="lesson-row-status">
                          {isCompleted ? (
                            <span className="lesson-status-completed" title={t('trainings.completed')}>
                              <Icon name="checkCircle" className="lesson-check-icon" />
                              <span className="visually-hidden">{t('trainings.completed')}</span>
                            </span>
                          ) : isNext ? (
                            <span className="lesson-next-tag">{t('trainings.nextUp')}</span>
                          ) : null}
                        </div>
                      </li>
                    )
                  })}
                </ol>
              </section>

              {/* Right Column: Course details & primary action */}
              <aside className="course-details-column" aria-label={title}>
                <div className="course-details-card">
                  <div className="course-hero-header">
                    <span className="course-level-tag">{t('trainings.levelBeginner')}</span>
                    <h1 className="course-page-title">{title}</h1>
                    <p className="course-page-summary">{summary}</p>
                  </div>

                  <dl className="course-specs-grid">
                    <div className="spec-item">
                      <dt className="spec-label">{t('trainings.levelBeginner')}</dt>
                      <dd className="spec-value">{t('trainings.levelBeginner')}</dd>
                    </div>
                    <div className="spec-item">
                      <dt className="spec-label">{t('trainings.singleLesson')}</dt>
                      <dd className="spec-value">
                        {t('trainings.lessonsCount', { count: course.lessons.length })}
                      </dd>
                    </div>
                    <div className="spec-item">
                      <dt className="spec-label">{t('trainings.minutesCount', { count: course.minutes })}</dt>
                      <dd className="spec-value">
                        {t('trainings.minutesCount', { count: course.minutes })}
                      </dd>
                    </div>
                    <div className="spec-item">
                      <dt className="spec-label">
                        {t('trainings.spokenLang', { lang: '' }).replace(/:\s*$/, '')}
                      </dt>
                      <dd className="spec-value">
                        {t(course.practice_lang === 'hi' ? 'trainings.langHi' : 'trainings.langEn')}
                      </dd>
                    </div>
                  </dl>

                  {whatYouPractise.length > 0 && (
                    <div className="what-you-practise-box">
                      <h3 className="what-you-practise-heading">{t('trainings.whatYouPractise')}</h3>
                      <ul className="what-you-practise-list">
                        {whatYouPractise.map((item, idx) => (
                          <li key={idx} className="what-practise-item">
                            <Icon name="check" className="what-practise-icon" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="course-action-wrap">
                    <PrimaryButton
                      className="course-primary-btn"
                      onClick={handleStartPractice}
                    >
                      {buttonLabel}
                    </PrimaryButton>

                    {!user && (
                      <p className="course-auth-hint">{t('trainings.signInToPractise')}</p>
                    )}

                    {practiceNotice && (
                      <p className="course-ready-notice" role="status">
                        {t('trainings.nextUp')}: {course.lessons[nextIndex]?.title?.[lang] || course.lessons[nextIndex]?.title?.en}
                      </p>
                    )}
                  </div>
                </div>
              </aside>
            </div>
          </>
        )}

        <HonestNote />
      </main>
    </div>
  )
}
