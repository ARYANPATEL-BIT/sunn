import { useLang } from '../i18n/index.jsx'
import { MAX_SECONDS } from '../record.jsx'
import { Icon } from './icons.jsx'
import { Label, Led } from './Label.jsx'

// The one orange key, seated in its well, with the listening light beside it and what tapping
// does printed under it. Tap to start, tap to stop. It dims while `waiting` for Prisma.
// The level display is the readout's blob; the key itself never shows the level.
export function PushButton({ recorder, onClick = recorder?.toggle, waiting, disabled, label, static: still, state: forced }) {
  const { t } = useLang()
  const state = forced || (recorder?.recording ? 'recording' : waiting ? 'waiting' : 'idle')
  const recording = state === 'recording'
  const words = recording ? (
    <>
      {t('sun.stop')}
      {recorder && (
        <span className="record-seconds">{t('sun.seconds', { seconds: recorder.seconds, max: MAX_SECONDS })}</span>
      )}
    </>
  ) : state === 'waiting' ? (
    t('sun.listening')
  ) : (
    label || t('sun.tap')
  )

  const key = (
    <span className="push-key" aria-hidden="true">
      <Icon name={recording ? 'stop' : 'mic'} />
    </span>
  )

  return (
    <div className={`push ${state}`}>
      <div className="push-well">
        <span className="push-light">
          <Led on={recording} />
          <Label k="device.listen" />
        </span>
        {still ? (
          <div className={`record ${state}`} aria-hidden="true">
            {key}
            <span className="record-label">{words}</span>
          </div>
        ) : (
          <button
            type="button"
            className={`record ${state}`}
            onClick={onClick}
            disabled={disabled || waiting}
            aria-busy={waiting || undefined}
          >
            {key}
            <span className="record-label">{words}</span>
          </button>
        )}
      </div>
      {waiting && !still && (
        <p className="visually-hidden" role="status">
          {t('sun.listening')}
        </p>
      )}
    </div>
  )
}
