import { useEffect, useState } from 'react'
import * as api from '../../api.js'
import { useLang } from '../../i18n/index.jsx'
import { Icon } from '../../ui/index.js'

export function IntroTipStep({ step }) {
  const { t, lang } = useLang()
  const [playing, setPlaying] = useState(false)

  const title = step.title?.[lang] || step.title?.en || ''
  const body = step.body?.[lang] || step.body?.en || ''

  useEffect(() => {
    return () => {
      api.stopAudio()
    }
  }, [step.id])

  const handlePlay = async () => {
    if (playing) {
      api.stopAudio()
      setPlaying(false)
      return
    }
    if (!step.audio_key) return
    setPlaying(true)
    try {
      await api.playAudioKey(step.audio_key)
    } finally {
      setPlaying(false)
    }
  }

  return (
    <div className="step-container step-intro-tip">
      <div className="step-card">
        {step.type === 'tip' && step.technique_id && (
          <div className="step-technique-pill">
            <Icon name="idea" className="step-technique-icon" />
            <span>
              {t('step.technique')}: {step.technique_id}
            </span>
          </div>
        )}

        <h2 className="step-main-title">{title}</h2>
        <p className="step-body-text">{body}</p>

        {step.audio_key && (
          <div className="step-audio-action">
            <button
              type="button"
              className="button step-listen-btn"
              onClick={handlePlay}
              aria-label={playing ? t('step.playing') : t('step.listenAudio')}
            >
              <Icon name={playing ? 'stop' : 'volume'} />
              <span>{playing ? t('step.playing') : t('step.listenAudio')}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
