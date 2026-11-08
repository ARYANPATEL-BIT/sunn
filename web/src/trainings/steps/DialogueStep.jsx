import { useEffect, useState } from 'react'
import * as api from '../../api.js'
import { useLang } from '../../i18n/index.jsx'
import { useRecorder } from '../../record.jsx'
import { Icon, PushButton } from '../../ui/index.js'

function SunnTurn({ turn }) {
  const { t } = useLang()
  const [playing, setPlaying] = useState(false)

  const handlePlay = async () => {
    if (!turn.audio_key) return
    if (playing) {
      api.stopAudio()
      setPlaying(false)
      return
    }
    setPlaying(true)
    try {
      await api.playAudioKey(turn.audio_key)
    } finally {
      setPlaying(false)
    }
  }

  return (
    <div className="dialogue-turn sunn-turn">
      <div className="turn-speaker-label">
        <span className="speaker-name">{t('dialogue.sunn')}</span>
      </div>
      <div className="turn-bubble sunn-bubble">
        <p className="turn-text" lang="hi">
          {turn.text}
        </p>
        {turn.latin && <p className="turn-latin">{turn.latin}</p>}

        {turn.audio_key && (
          <button
            type="button"
            className="button small turn-listen-btn"
            onClick={handlePlay}
            aria-label={playing ? t('step.playing') : t('step.listenAudio')}
          >
            <Icon name={playing ? 'stop' : 'volume'} />
            <span>{playing ? t('step.playing') : t('step.listenAudio')}</span>
          </button>
        )}
      </div>
    </div>
  )
}

function YouTurn({ turn }) {
  const { t } = useLang()
  const allChoices = [{ text: turn.text, latin: turn.latin }, ...(turn.options || [])]
  const [selectedIdx, setSelectedIdx] = useState(0)
  const currentChoice = allChoices[selectedIdx] || allChoices[0]
  const recorder = useRecorder(() => {})

  return (
    <div className="dialogue-turn you-turn">
      <div className="turn-speaker-label">
        <span className="speaker-name">{t('dialogue.you')}</span>
      </div>
      <div className="turn-bubble you-bubble">
        {allChoices.length > 1 && (
          <div className="turn-options-selector">
            <span className="options-selector-label">{t('dialogue.chooseOption')}</span>
            <div className="options-chips">
              {allChoices.map((c, i) => (
                <button
                  key={i}
                  type="button"
                  className={`chip ${i === selectedIdx ? 'active' : ''}`}
                  onClick={() => setSelectedIdx(i)}
                >
                  {c.text}
                </button>
              ))}
            </div>
          </div>
        )}

        <p className="turn-text current-spoken-text" lang="hi">
          {currentChoice.text}
        </p>
        {currentChoice.latin && <p className="turn-latin">{currentChoice.latin}</p>}

        <div className="turn-record-seat">
          <PushButton recorder={recorder} />
        </div>
      </div>
    </div>
  )
}

export function DialogueStep({ step }) {
  const { t, lang } = useLang()
  const title = step.title?.[lang] || step.title?.en || ''
  const scenario = step.scenario?.[lang] || step.scenario?.en || ''
  const turns = step.turns || []

  useEffect(() => {
    return () => {
      api.stopAudio()
    }
  }, [step.id])

  return (
    <div className="step-container step-dialogue">
      <div className="step-card">
        <h2 className="step-main-title">{title}</h2>

        {scenario && (
          <div className="dialogue-scenario-box">
            <span className="scenario-label">{t('dialogue.scenario')}</span>
            <p className="scenario-text">{scenario}</p>
          </div>
        )}

        <div className="dialogue-turns-flow">
          {turns.map((turn, idx) =>
            turn.speaker === 'sunn' ? (
              <SunnTurn key={idx} turn={turn} />
            ) : (
              <YouTurn key={idx} turn={turn} />
            ),
          )}
        </div>
      </div>
    </div>
  )
}
