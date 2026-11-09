import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import * as api from '../api.js'
import { useAuth } from '../auth.jsx'
import { useLang } from '../i18n/index.jsx'
import { Alert, Icon, reducedMotion } from '../ui/index.js'
import { HonestNote } from './HonestNote.jsx'
import { TrainingsNav } from './TrainingsNav.jsx'

export function CategoryPage() {
  const { categoryId } = useParams()
  const { user } = useAuth()
  const { t, lang } = useLang()
  const [category, setCategory] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadCategory = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getTrainingsCategory(categoryId)
      setCategory(data)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCategory()
  }, [categoryId, user])

  const title = category?.title?.[lang] || category?.title?.en || ''
  const subtitle = category?.subtitle?.[lang] || category?.subtitle?.en || ''
  const description = category?.description?.[lang] || category?.description?.en || ''

  return (
    <div className={`trainings-page ${user ? 'with-tabs' : ''}`}>
      <TrainingsNav backTo="/trainings" backLabel={t('trainings.backToTrainings')} />

      <main className="trainings-content" id="category-main">
        {loading && (
          <div className="trainings-skeletons" aria-busy="true" aria-label={t('app.loading')}>
            <div className="skeleton-line title" />
            <div className="skeleton-line lede" />
            <div className="skeleton-card" />
            <div className="skeleton-card" />
          </div>
        )}

        {error && (
          <div className="trainings-error">
            <Alert error={error} />
            <button type="button" className="button" onClick={loadCategory}>
              {t('trainings.retry')}
            </button>
          </div>
        )}

        {!loading && !error && category && (
          <>
            <header className="category-header-section">
              <div className="category-title-row">
                <div className="category-hero-icon" aria-hidden="true">
                  <Icon name={category.icon} />
                </div>
                <div>
                  <h1 className="display category-page-title">{title}</h1>
                  {subtitle && <p className="category-page-subtitle">{subtitle}</p>}
                </div>
              </div>
              {description && <p className="category-page-description">{description}</p>}
            </header>

            <section className="category-courses-section" aria-label={title}>
              {category.courses.length === 0 ? (
                <p className="trainings-empty">{t('trainings.emptyCourses')}</p>
              ) : (
                <div className="courses-list">
                  {category.courses.map((course) => {
                    const courseTitle = course.title[lang] || course.title.en
                    const courseSummary = course.summary[lang] || course.summary.en
                    const hasProgress = course.percent != null && course.percent > 0
                    const actionLabel = hasProgress ? t('trainings.continueAction') : t('trainings.startAction')

                    return (
                      <article key={course.id} className="course-card">
                        <div className="course-card-main">
                          <div className="course-card-tags">
                            <span className="course-level-tag">{t('trainings.levelBeginner')}</span>
                            <span className="course-meta-bullet" aria-hidden="true">
                              ·
                            </span>
                            <span className="course-meta-item">
                              {t(course.lesson_count === 1 ? 'trainings.singleLesson' : 'trainings.lessonsCount', {
                                count: course.lesson_count,
                              })}
                            </span>
                            <span className="course-meta-bullet" aria-hidden="true">
                              ·
                            </span>
                            <span className="course-meta-item">
                              {t('trainings.minutesCount', { count: course.minutes })}
                            </span>
                          </div>

                          <h2 className="course-card-title">
                            <Link
                              to={`/trainings/${category.id}/${course.id}`}
                              className="course-card-link"
                              viewTransition={!reducedMotion()}
                            >
                              {courseTitle}
                            </Link>
                          </h2>
                          <p className="course-card-summary">{courseSummary}</p>

                          {course.percent != null && (
                            <div className="trainings-progress-wrap">
                              <div
                                className="trainings-progress-bar"
                                role="progressbar"
                                aria-valuenow={course.percent}
                                aria-valuemin={0}
                                aria-valuemax={100}
                              >
                                <div
                                  className="trainings-progress-fill"
                                  style={{ width: `${course.percent}%` }}
                                />
                              </div>
                              <span className="trainings-progress-label">
                                {t('trainings.progressPercent', { percent: course.percent })}
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="course-card-action">
                          <Link
                            to={`/trainings/${category.id}/${course.id}`}
                            className={`button ${hasProgress ? 'primary' : ''}`}
                            viewTransition={!reducedMotion()}
                          >
                            {actionLabel}
                          </Link>
                        </div>
                      </article>
                    )
                  })}
                </div>
              )}
            </section>
          </>
        )}

        <HonestNote />
      </main>
    </div>
  )
}
