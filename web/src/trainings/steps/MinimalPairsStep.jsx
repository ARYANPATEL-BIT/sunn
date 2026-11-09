import { useEffect, useState } from 'react'
import * as api from '../../api.js'
import { useLang } from '../../i18n/index.jsx'
import { useRecorder } from '../../record.jsx'
import { Icon, PushButton } from '../../ui/index.js'

function PairCard({ item, sound, label }) {
  const { t } = useLang()
  const [playing, setPlaying] = useState(false)
  const recorder = useRecorder(() => {})

  const handlePlay = async () => {
    if (!item?.audio_key) return
    if (playing) {
      api.stopAudio()
      setPlaying(false)
      return
    }
    setPlaying(true)
    try {
      await api.playAudioKey(item.audio_key)
    } finally {
      setPlaying(false)
    }
  }

  return (
    <div className="pair-card">
      <div className="pair-card-header">
        <span className="pair-label-kicker">{label}</span>
        {sound && (
          <div className="pair-sound-indicator">
            <span className="yellow-accent-bar" aria-hidden="true" />
            <span className="pair-sound-text">{t('minimalPairs.sound', { sound })}</span>
          </div>
        )}
      </div>

      <div className="pair-card-body">
        <p className="pair-card-text" lang="hi">
          {item.text}
        </p>
        {item.latin && <p className="pair-card-latin">{item.latin}</p>}
      </div>

      <div className="pair-card-actions">
        {item.audio_key && (
          <button
            type="button"
            className="button small"
            onClick={handlePlay}
            aria-label={playing ? t('step.playing') : t('listenRepeat.listen')}
          >
            <Icon name={playing ? 'stop' : 'volume'} />
            <span>{playing ? t('step.playing') : t('listenRepeat.listen')}</span>
          </button>
        )}

        <div className="pair-record-seat">
          <PushButton recorder={recorder} />
        </div>
      </div>
    </div>
  )
}

export function MinimalPairsStep({ step }) {
  const { t, lang } = useLang()
  const pairs = step.pairs || []
  const [pairIndex, setPairIndex] = useState(0)

  const currentPair = pairs[pairIndex] || pairs[0]
  const title = step.title?.[lang] || step.title?.en || ''

  useEffect(() => {
    api.stopAudio()
  }, [pairIndex, step.id])

  if (!currentPair) return null

  return (
    <div className="step-container step-minimal-pairs">
      <div className="step-card">
        <h2 className="step-main-title">{title}</h2>

        <div className="minimal-pairs-grid">
          <PairCard item={currentPair.a} sound={currentPair.sound_a} label="A" />
          <PairCard item={currentPair.b} sound={currentPair.sound_b} label="B" />
        </div>

        {pairs.length > 1 && (
          <div className="item-nav-row">
            <button
              type="button"
              className="button small"
              disabled={pairIndex === 0}
              onClick={() => setPairIndex((i) => i - 1)}
            >
              <Icon name="chevronLeft" />
              <span>{t('minimalPairs.prevPair')}</span>
            </button>

            <span className="item-counter">
              {t('minimalPairs.pairCounter', {
                current: pairIndex + 1,
                total: pairs.length,
              })}
            </span>

            <button
              type="button"
              className="button small"
              disabled={pairIndex === pairs.length - 1}
              onClick={() => setPairIndex((i) => i + 1)}
            >
              <span>{t('minimalPairs.nextPair')}</span>
              <Icon name="chevronRight" />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
