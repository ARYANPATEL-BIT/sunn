import { Link } from 'react-router-dom'
import { useLang } from '../i18n/index.jsx'
import { Icon, PrimaryButton, reducedMotion } from '../ui/index.js'

export function LessonDone({
  lesson,
  course,
  categoryId,
  onNextLesson,
  onBackToCourse,
}) {
  const { t } = useLang()
  const isReduced = reducedMotion()

  const completedCount =
    (course?.lessons?.filter((l) => l.completed).length || 0) +
    (course?.lessons?.some((l) => l.id === lesson.id && l.completed) ? 0 : 1)
  const totalCount = course?.lessons?.length || 1

  return (
    <div className="step-container lesson-done-container">
      <div className="step-card lesson-done-card">
        <div className={`celebration-badge ${isReduced ? 'reduced' : 'pop'}`}>
          <Icon name="checkCircle" className="celebration-icon" />
        </div>

        <h1 className="lesson-done-title">{t('lesson.doneTitle')}</h1>
        <p className="lesson-done-subtitle">{t('lesson.doneSubtitle')}</p>

        <div className="lesson-done-stats">
          <div className="done-stat-box">
            <span className="done-stat-val">
              {t('lesson.minutesPractised', { count: lesson.minutes })}
            </span>
          </div>

          <div className="done-stat-box">
            <span className="done-stat-val">
              {t('lesson.courseProgress', {
                completed: completedCount,
                total: totalCount,
              })}
            </span>
          </div>
        </div>

        <div className="lesson-done-actions">
          {lesson.next_lesson_id ? (
            <PrimaryButton className="done-next-btn" onClick={onNextLesson}>
              <Icon name="play" />
              <span>{t('lesson.nextLesson')}</span>
            </PrimaryButton>
          ) : null}

          <button
            type="button"
            className={`button ${!lesson.next_lesson_id ? 'primary' : ''}`}
            onClick={onBackToCourse}
          >
            <Icon name="arrowLeft" />
            <span>{t('lesson.backToCourse')}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
