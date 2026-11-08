import { useEffect, useRef, useState } from 'react'
import { useLang } from '../../i18n/index.jsx'
import { Icon, reducedMotion } from '../../ui/index.js'

export function BreathingStep({ step }) {
  const { t, lang } = useLang()
  const inSeconds = step.pattern?.in_s || 3
  const outSeconds = step.pattern?.out_s || 4
  const totalRounds = step.rounds || 4

  const [active, setActive] = useState(false)
  const [phase, setPhase] = useState('ready') // 'ready' | 'in' | 'out'
  const [round, setRound] = useState(1)
  const [secondsLeft, setSecondsLeft] = useState(inSeconds)
  const isReduced = reducedMotion()

  const timerRef = useRef(null)

  const title = step.title?.[lang] || step.title?.en || ''
  const body = step.body?.[lang] || step.body?.en || ''

  useEffect(() => {
    if (!active) {
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }

    if (phase === 'ready') {
      setPhase('in')
      setSecondsLeft(inSeconds)
    }

    timerRef.current = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev > 1) return prev - 1

        // Phase transition
        setPhase((currPhase) => {
          if (currPhase === 'in') {
            return 'out'
          } else {
            setRound((currRound) => (currRound < totalRounds ? currRound + 1 : currRound))
            return 'in'
          }
        })

        return phase === 'in' ? outSeconds : inSeconds
      })
    }, 1000)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [active, phase, inSeconds, outSeconds, totalRounds])

  const toggleActive = () => {
    setActive((prev) => !prev)
  }

  const phaseText =
    phase === 'in'
      ? t('breathing.in')
      : phase === 'out'
        ? t('breathing.out')
        : t('breathing.ready')

  const circleScaleClass =
    !active || phase === 'ready'
      ? 'scale-ready'
      : phase === 'in'
        ? 'scale-in'
        : 'scale-out'

  const transitionDuration = phase === 'in' ? `${inSeconds}s` : `${outSeconds}s`

  return (
    <div className="step-container step-breathing">
      <div className="step-card">
        <h2 className="step-main-title">{title}</h2>
        {body && <p className="step-body-text">{body}</p>}

        <div className="breathing-round-meta">
          <span className="breathing-round-badge">
            {t('breathing.roundCounter', { current: round, total: totalRounds })}
          </span>
        </div>

        <div className="breathing-circle-stage">
          <div
            className={`breathing-circle ${isReduced ? 'reduced' : circleScaleClass}`}
            style={{
              transitionDuration: isReduced ? '0s' : transitionDuration,
            }}
          >
            <div className="breathing-circle-content">
              <span className="breathing-phase-text">{phaseText}</span>
              {active && (
                <span className="breathing-seconds-text" aria-live="off">
                  {t('breathing.countdown', { seconds: secondsLeft })}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="breathing-controls">
          <button
            type="button"
            className="button primary breathing-toggle-btn"
            onClick={toggleActive}
            aria-pressed={active}
          >
            <Icon name={active ? 'pause' : 'play'} />
            <span>{t(active ? 'breathing.pause' : 'breathing.start')}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
