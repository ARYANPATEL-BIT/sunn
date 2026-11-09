import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import * as api from '../api.js'
import { useAuth } from '../auth.jsx'
import { useLang } from '../i18n/index.jsx'
import { Alert, Icon, PrimaryButton, reducedMotion } from '../ui/index.js'
import { LessonsLangNote } from './HonestNote.jsx'
import { LessonDone } from './LessonDone.jsx'
import { StepView } from './steps/index.jsx'

export function LessonPlayer() {
  const { categoryId, courseId, lessonId } = useParams()
  const { user } = useAuth()
  const { t, lang } = useLang()
  const navigate = useNavigate()

  const [lesson, setLesson] = useState(null)
  const [course, setCourse] = useState(null)
  const [stepIndex, setStepIndex] = useState(0)
  const [isDone, setIsDone] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const announcedStepRef = useRef('')

  const courseBackPath = `/trainings/${categoryId}/${courseId}`

  // Load lesson and course data, and resume step if available
  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [lessonData, courseData, progressData] = await Promise.all([
        api.getTrainingsLesson(lessonId),
        api.getTrainingsCourse(courseId).catch(() => null),
        user ? api.getTrainingsProgress().catch(() => null) : null,
      ])

      setLesson(lessonData)
      setCourse(courseData)

      // Query param override (e.g. ?step=3 or ?done=1) or resume at saved step
      const searchParams = new URLSearchParams(window.location.search)
      const stepParam = searchParams.get('step')
      const doneParam = searchParams.get('done')

      if (doneParam === '1') {
        setIsDone(true)
        setStepIndex((lessonData.steps?.length || 1) - 1)
      } else if (
        stepParam !== null &&
        !isNaN(Number(stepParam)) &&
        Number(stepParam) >= 0 &&
        Number(stepParam) < (lessonData.steps?.length || 0)
      ) {
        setStepIndex(Number(stepParam))
      } else {
        const localStep = localStorage.getItem(`sunn.lesson.${lessonId}.step`)
        if (
          localStep !== null &&
          Number(localStep) >= 0 &&
          Number(localStep) < (lessonData.steps?.length || 0)
        ) {
          setStepIndex(Number(localStep))
        } else if (
          progressData?.resume?.lesson_id === lessonId &&
          typeof progressData.resume.step_index === 'number' &&
          progressData.resume.step_index < (lessonData.steps?.length || 0)
        ) {
          setStepIndex(progressData.resume.step_index)
        } else {
          setStepIndex(0)
        }
      }
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    return () => {
      api.stopAudio()
    }
  }, [lessonId, courseId, user])

  // Save progress on step changes (when signed in)
  const goToStep = async (newIndex) => {
    if (!lesson?.steps) return
    if (newIndex < 0 || newIndex >= lesson.steps.length) return

    api.stopAudio()
    setStepIndex(newIndex)
    setIsDone(false)
    try {
      localStorage.setItem(`sunn.lesson.${lesson.id}.step`, String(newIndex))
    } catch {
      // Local storage unavailable
    }

    if (user) {
      try {
        await api.saveTrainingsProgress(lesson.id, newIndex, false)
      } catch {
        // Non-fatal if offline
      }
    }
  }

  const handleNext = async () => {
    if (!lesson?.steps) return
    if (stepIndex < lesson.steps.length - 1) {
      goToStep(stepIndex + 1)
    } else {
      // Last step: finish lesson
      api.stopAudio()
      setIsDone(true)
      try {
        localStorage.removeItem(`sunn.lesson.${lesson.id}.step`)
      } catch {
        // Local storage cleanup
      }
      if (user) {
        try {
          await api.saveTrainingsProgress(lesson.id, stepIndex, true)
        } catch {
          // Non-fatal
        }
      }
    }
  }

  const handleBack = () => {
    if (isDone) {
      setIsDone(false)
      return
    }
    if (stepIndex > 0) {
      goToStep(stepIndex - 1)
    }
  }

  const handleClose = () => {
    api.stopAudio()
    navigate(courseBackPath, { viewTransition: !reducedMotion() })
  }

  const handleNextLesson = () => {
    if (lesson?.next_lesson_id) {
      api.stopAudio()
      navigate(`/trainings/${categoryId}/${courseId}/${lesson.next_lesson_id}`, {
        viewTransition: !reducedMotion(),
      })
    } else {
      handleClose()
    }
  }

  // Keyboard navigation: Escape closes lesson, Enter advances (when not focused on a control)
  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === 'Escape') {
        e.preventDefault()
        handleClose()
      } else if (e.key === 'Enter') {
        const tag = document.activeElement?.tagName
        if (tag === 'BUTTON' || tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'A') return
        e.preventDefault()
        handleNext()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [stepIndex, isDone, lesson])

  const totalSteps = lesson?.steps?.length || 1
  const currentStep = lesson?.steps?.[stepIndex]
  const courseTitle = course?.title?.[lang] || course?.title?.en || ''
  const lessonTitle = lesson?.title?.[lang] || lesson?.title?.en || ''
  const stepTitle = currentStep?.title?.[lang] || currentStep?.title?.en || ''

  const isLastStep = stepIndex === totalSteps - 1
  const stepAnnouncement = currentStep
    ? t('lesson.stepAnnouncement', {
        current: stepIndex + 1,
        total: totalSteps,
        title: stepTitle,
      })
    : ''

  return (
    <div className="lesson-player-page">
      {/* Top Header */}
      <header className="lesson-player-header">
        <div className="player-header-inner">
          <div className="player-header-top">
            <Link
              to={courseBackPath}
              className="player-course-link"
              onClick={() => api.stopAudio()}
              viewTransition={!reducedMotion()}
            >
              <Icon name="arrowLeft" />
              <span>{courseTitle || t('lesson.backToCourse')}</span>
            </Link>

            <button
              type="button"
              className="icon-button close-lesson-btn"
              onClick={handleClose}
              aria-label={t('lesson.close')}
            >
              <Icon name="x" />
            </button>
          </div>

          <div className="player-meta-row">
            <h1 className="player-lesson-title">{lessonTitle}</h1>
            <span className="player-step-counter">
              {t('lesson.stepCounter', {
                current: isDone ? totalSteps : stepIndex + 1,
                total: totalSteps,
              })}
            </span>
          </div>

          {/* Segmented progress bar (segments, not dots) */}
          <div
            className="segmented-meter"
            role="progressbar"
            aria-valuenow={isDone ? totalSteps : stepIndex + 1}
            aria-valuemin={1}
            aria-valuemax={totalSteps}
          >
            {lesson?.steps?.map((_, idx) => (
              <span
                key={idx}
                className={`meter-segment ${idx <= (isDone ? totalSteps : stepIndex) ? 'active' : ''}`}
              />
            ))}
          </div>
        </div>
      </header>
      <LessonsLangNote />

      {/* Screen reader live announcement */}
      <div aria-live="polite" className="visually-hidden">
        {stepAnnouncement}
      </div>

      {/* Middle Step Content */}
      <main className="lesson-player-main" id="lesson-main">
        {loading && (
          <div className="lesson-player-skeleton" aria-busy="true" aria-label={t('app.loading')}>
            <div className="skeleton-card" />
          </div>
        )}

        {error && (
          <div className="lesson-player-error">
            <Alert error={error} />
            <button type="button" className="button" onClick={loadData}>
              {t('trainings.retry')}
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            {isDone ? (
              <LessonDone
                lesson={lesson}
                course={course}
                categoryId={categoryId}
                onNextLesson={handleNextLesson}
                onBackToCourse={handleClose}
              />
            ) : (
              <StepView
                step={currentStep}
                lessonId={lesson?.id}
                categoryId={categoryId || lesson?.category_id}
              />
            )}
          </>
        )}
      </main>

      {/* Bottom Navigation Bar */}
      {!loading && !error && !isDone && (
        <footer className="lesson-player-footer">
          <div className="player-footer-inner">
            <button
              type="button"
              className="button player-nav-btn player-back-btn"
              onClick={handleBack}
              disabled={stepIndex === 0}
            >
              <Icon name="chevronLeft" />
              <span>{t('lesson.backAction')}</span>
            </button>

            <PrimaryButton
              className="player-nav-btn player-next-btn"
              onClick={handleNext}
            >
              <span>{isLastStep ? t('lesson.finishAction') : t('lesson.nextAction')}</span>
              {!isLastStep && <Icon name="chevronRight" />}
            </PrimaryButton>
          </div>
        </footer>
      )}
    </div>
  )
}
