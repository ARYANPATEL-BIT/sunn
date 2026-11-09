import { useLang } from '../i18n/index.jsx'
import { Icon, PrimaryButton } from '../ui/index.js'

function KidsBuddy({ message }) {
  return (
    <div className="kids-reaction-stage" role="status">
      <svg
        viewBox="0 0 64 64"
        width="64"
        height="64"
        className="kids-buddy-svg"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="32" cy="32" r="24" />
        <circle cx="24" cy="28" r="2.5" fill="currentColor" />
        <circle cx="40" cy="28" r="2.5" fill="currentColor" />
        <path d="M22 36c2.5 5 17.5 5 20 0" />
        <path d="M16 14l4 8M48 14l-4 8" />
      </svg>
      <p className="kids-reaction-msg">{message}</p>
    </div>
  )
}

export function CheckingFeedback({
  hasRecording,
  attempt,
  checking,
  onCheck,
  onPractiseAgain,
  feedbackType = 'pace',
  isKids = false,
  isSmoothOrKids = false,
  checksLeftToday = 20,
}) {
  const { t } = useLang()

  if (!hasRecording) return null

  const isExhausted = checksLeftToday === 0

  return (
    <div className="checking-feedback-box" aria-live="polite">
      {!attempt && (
        <div className="check-decision-actions">
          <div className="check-main-btn-wrap">
            <PrimaryButton
              className="check-reading-btn"
              onClick={onCheck}
              disabled={checking || isExhausted}
            >
              <Icon name="check" />
              <span>{checking ? t('check.checking') : t('check.checkAction')}</span>
            </PrimaryButton>

            {!isKids && (
              <span className="checks-counter-meta">
                {isExhausted
                  ? t('check.noChecksLeft')
                  : t('check.checksLeft', { count: checksLeftToday ?? 20 })}
              </span>
            )}
          </div>

          <button
            type="button"
            className="button practise-again-btn"
            onClick={onPractiseAgain}
            disabled={checking}
          >
            <Icon name="rotate" />
            <span>{t('check.practiseAgain')}</span>
          </button>
        </div>
      )}

      {attempt && (
        <div className="check-results-stage">
          {/* Kids character reaction */}
          {isKids && (
            <KidsBuddy message={t('kids.greatTry')} />
          )}

          {/* Supportive message: for feedback 'none', show only the supportive note */}
          {feedbackType === 'none' ? (
            <p className="check-supportive-message check-none-text">
              {t('check.feedbackNone')}
            </p>
          ) : (
            attempt.message_key && (
              <p className="check-supportive-message">
                {t(`check.message_${attempt.message_key}`)}
              </p>
            )
          )}

          {/* Words feedback (only when NOT smooth-speaking and NOT kids-speaking) */}
          {attempt.checked && attempt.words && !isSmoothOrKids && (
            <div className="words-check-grid" aria-label={t('trainings.whatYouPractise')}>
              {attempt.words.map((w, idx) => (
                <div key={idx} className={`word-check-card ${w.status}`}>
                  <span className="word-text" lang="hi">
                    {w.text}
                  </span>
                  {w.status === 'practise' && (
                    <span className="word-practise-tag">{t('check.wordPractise')}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Pace scale feedback */}
          {attempt.checked && attempt.pace && (
            <div
              className="pace-scale-box"
              role="region"
              aria-label={t('check.paceScaleLabel')}
            >
              <div className="pace-scale-track">
                <span
                  className={`pace-segment slower ${attempt.pace === 'slower' ? 'active' : ''}`}
                >
                  {t('check.paceSlower')}
                </span>
                <span className="pace-sep" aria-hidden="true">
                  ·
                </span>
                <span
                  className={`pace-segment good ${attempt.pace === 'good' ? 'active' : ''}`}
                >
                  {t('check.paceGood')}
                </span>
                <span className="pace-sep" aria-hidden="true">
                  ·
                </span>
                <span
                  className={`pace-segment faster ${attempt.pace === 'faster' ? 'active' : ''}`}
                >
                  {t('check.paceFaster')}
                </span>
              </div>
              <p className="pace-desc-text">
                {t(`check.paceMarker_${attempt.pace}`)}
              </p>
            </div>
          )}

          <div className="check-results-actions">
            <button
              type="button"
              className="button practise-again-btn"
              onClick={onPractiseAgain}
            >
              <Icon name="rotate" />
              <span>{t('check.practiseAgain')}</span>
            </button>

            {!isKids && attempt.checks_left_today != null && (
              <span className="checks-counter-meta">
                {t('check.checksLeft', { count: attempt.checks_left_today })}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
