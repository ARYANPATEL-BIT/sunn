import { useEffect, useState } from 'react'
import * as api from '../../api.js'
import { useAuth } from '../../auth.jsx'
import { useLang } from '../../i18n/index.jsx'
import { useRecorder } from '../../record.jsx'
import { Icon, PushButton } from '../../ui/index.js'
import { CheckingFeedback } from '../CheckingFeedback.jsx'

export function ReadAloudStep({ step, isKids = false, isSmoothOrKids = false }) {
  const { user } = useAuth()
  const { t, lang } = useLang()
  const [playing, setPlaying] = useState(false)
  const [recordedBlob, setRecordedBlob] = useState(null)
  const [attemptResult, setAttemptResult] = useState(null)
  const [checking, setChecking] = useState(false)
  const [checksLeft, setChecksLeft] = useState(24)

  const title = step.title?.[lang] || step.title?.en || ''

  const recorder = useRecorder(async (blob) => {
    setRecordedBlob(blob)
    setAttemptResult(null)
    if (user) {
      try {
        await api.postTrainingsAttempt(blob, step.id, null, false)
      } catch {
        // Non-blocking
      }
    }
  })

  useEffect(() => {
    setRecordedBlob(null)
    setAttemptResult(null)
    api.stopAudio()
    setPlaying(false)
  }, [step.id])

  const handlePlay = async () => {
    if (!step.audio_key) return
    if (playing) {
      api.stopAudio()
      setPlaying(false)
      return
    }
    setPlaying(true)
    try {
      await api.playAudioKey(step.audio_key)
    } finally {
      setPlaying(false)
    }
  }

  const handleCheck = async () => {
    if (!recordedBlob) return
    setChecking(true)
    try {
      const res = await api.postTrainingsAttempt(recordedBlob, step.id, null, true)
      setAttemptResult(res)
      if (res?.checks_left_today != null) {
        setChecksLeft(res.checks_left_today)
      }
    } catch {
      // Non-blocking
    } finally {
      setChecking(false)
    }
  }

  const handlePractiseAgain = () => {
    setRecordedBlob(null)
    setAttemptResult(null)
  }

  return (
    <div className={`step-container step-read-aloud ${isKids ? 'is-kids' : ''}`}>
      <div className="step-card">
        <h2 className="step-main-title">{title}</h2>

        <div className="read-aloud-box">
          <p className="read-aloud-paragraph" lang="hi">
            {step.paragraph}
          </p>
          {step.latin && <p className="read-aloud-latin">{step.latin}</p>}
        </div>

        <div className="read-aloud-actions">
          {step.audio_key && (
            <button
              type="button"
              className="button read-listen-btn"
              onClick={handlePlay}
              aria-label={playing ? t('step.playing') : t('readAloud.listenSunn')}
            >
              <Icon name={playing ? 'stop' : 'volume'} />
              <span>{playing ? t('step.playing') : t('readAloud.listenSunn')}</span>
            </button>
          )}

          <div className="record-seat">
            <PushButton recorder={recorder} />
          </div>
        </div>

        <CheckingFeedback
          hasRecording={Boolean(recordedBlob)}
          attempt={attemptResult}
          checking={checking}
          onCheck={handleCheck}
          onPractiseAgain={handlePractiseAgain}
          feedbackType={step.feedback || 'words'}
          isKids={isKids}
          isSmoothOrKids={isSmoothOrKids}
          checksLeftToday={checksLeft}
        />
      </div>
    </div>
  )
}
