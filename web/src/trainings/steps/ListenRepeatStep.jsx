import { useEffect, useState } from 'react'
import * as api from '../../api.js'
import { useAuth } from '../../auth.jsx'
import { useLang } from '../../i18n/index.jsx'
import { useRecorder } from '../../record.jsx'
import { Icon, PushButton } from '../../ui/index.js'
import { CheckingFeedback } from '../CheckingFeedback.jsx'

export function ListenRepeatStep({ step, isKids = false, isSmoothOrKids = false }) {
  const { user } = useAuth()
  const { t, lang } = useLang()
  const items = step.items || []
  const [itemIndex, setItemIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [recordedBlob, setRecordedBlob] = useState(null)
  const [attemptResult, setAttemptResult] = useState(null)
  const [checking, setChecking] = useState(false)
  const [checksLeft, setChecksLeft] = useState(20)

  const currentItem = items[itemIndex] || items[0]
  const title = step.title?.[lang] || step.title?.en || ''

  const recorder = useRecorder(async (blob) => {
    setRecordedBlob(blob)
    setAttemptResult(null)
    if (user && currentItem) {
      try {
        await api.postTrainingsAttempt(blob, step.id, currentItem.id, false)
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
  }, [itemIndex, step.id])

  const handlePlay = async () => {
    if (!currentItem?.audio_key) return
    if (playing) {
      api.stopAudio()
      setPlaying(false)
      return
    }
    setPlaying(true)
    try {
      await api.playAudioKey(currentItem.audio_key)
    } finally {
      setPlaying(false)
    }
  }

  const handleCheck = async () => {
    if (!recordedBlob || !currentItem) return
    setChecking(true)
    try {
      const res = await api.postTrainingsAttempt(recordedBlob, step.id, currentItem.id, true)
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

  if (!currentItem) return null

  return (
    <div className={`step-container step-listen-repeat ${isKids ? 'is-kids' : ''}`}>
      <div className="step-card">
        <div className="step-header-row">
          <h2 className="step-main-title">{title}</h2>
          {currentItem.focus_sound && (
            <span className="step-focus-badge">
              {t('listenRepeat.focus', { sound: currentItem.focus_sound })}
            </span>
          )}
        </div>

        <div className="phrase-hero-stage">
          <p className="phrase-main-text" lang="hi">
            {currentItem.text}
          </p>
          {currentItem.latin && <p className="phrase-latin-text">{currentItem.latin}</p>}
          {currentItem.meaning_en && (
            <p className="phrase-meaning-text">{currentItem.meaning_en}</p>
          )}
        </div>

        <div className="listen-repeat-actions">
          {currentItem.audio_key && (
            <button
              type="button"
              className="button listen-audio-btn"
              onClick={handlePlay}
              aria-label={playing ? t('step.playing') : t('listenRepeat.listen')}
            >
              <Icon name={playing ? 'stop' : 'volume'} />
              <span>{playing ? t('step.playing') : t('listenRepeat.listen')}</span>
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

        {items.length > 1 && (
          <div className="item-nav-row">
            <button
              type="button"
              className="button small"
              disabled={itemIndex === 0}
              onClick={() => setItemIndex((i) => i - 1)}
            >
              <Icon name="chevronLeft" />
              <span>{t('listenRepeat.prevItem')}</span>
            </button>

            <span className="item-counter">
              {t('listenRepeat.itemCounter', {
                current: itemIndex + 1,
                total: items.length,
              })}
            </span>

            <button
              type="button"
              className="button small"
              disabled={itemIndex === items.length - 1}
              onClick={() => setItemIndex((i) => i + 1)}
            >
              <span>{t('listenRepeat.nextItem')}</span>
              <Icon name="chevronRight" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
