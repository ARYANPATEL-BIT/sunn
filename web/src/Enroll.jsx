import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { NEEDED, getGoalOptions, needsRerecord, ready, speakProgress } from './quickstart.js'
import { useRecorder } from './record.jsx'
import { Alert, Button, Grille, Label, PrimaryButton, PushButton, Readout, ReadoutRow, useGo } from './ui/index.js'

// One phrase at a time, NEEDED saved recordings each, prioritized by the chosen initial goal.
// Every save is stored on the server, so leaving is pausing: coming back resumes at the first
// phrase that still needs recordings. Recording here is the same device as Speak: readout, blob, key.
export default function Enroll() {
  const { t } = useLang()
  const { user, updateUser } = useAuth()
  const go = useGo()
  const { state } = useLocation()
  const [phrases, setPhrases] = useState(null)
  const [blob, setBlob] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [choosingGoal, setChoosingGoal] = useState(false)
  const [selectedGoal, setSelectedGoal] = useState(user?.phrase_goal || 10)
  const recorder = useRecorder(setBlob)

  async function run(action) {
    setBusy(true)
    setError(null)
    try {
      await action()
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const load = () => run(async () => setPhrases(await api.listPhrases()))
  useEffect(() => {
    load()
    return () => {
      api.stopAudio()
    }
  }, [])

  useEffect(() => {
    if (user?.phrase_goal) {
      setSelectedGoal(user.phrase_goal)
    }
  }, [user?.phrase_goal])

  useEffect(() => {
    if (state?.chooseGoal) {
      setChoosingGoal(true)
    }
  }, [state])

  useEffect(() => {
    if (phrases && phrases.length > 0) {
      if (!user?.phrase_goal) {
        setChoosingGoal(true)
      }
    }
  }, [phrases, user?.phrase_goal])

  if (!phrases) {
    return (
      <section className="screen narrow">
        <Alert error={error} />
        {error && (
          <Button onClick={load} disabled={busy}>
            {t('error.retry')}
          </Button>
        )}
      </section>
    )
  }

  if (phrases.length === 0) {
    return (
      <section className="screen narrow empty-state">
        <h1 className="large-title">{t('enroll.empty')}</h1>
        {state?.phrasesFailed && <p className="note">{t('signup.phrasesFailed')}</p>}
        <p className="lede-sm">{t('enroll.emptyBody')}</p>
        <Alert error={error} />
        <PrimaryButton disabled={busy} onClick={() => run(async () => setPhrases(await api.loadDefaultPhrases()))}>
          {t(busy ? 'enroll.adding' : 'enroll.addDefaults')}
        </PrimaryButton>
      </section>
    )
  }

  async function confirmGoal() {
    await run(async () => {
      await api.updateMe({ phrase_goal: selectedGoal })
      if (updateUser) {
        updateUser({ phrase_goal: selectedGoal })
      }
      try {
        localStorage.setItem(`goal_confirmed_${user?.id}`, '1')
      } catch {}
      setChoosingGoal(false)
    })
  }

  const goalOptions = getGoalOptions(phrases.length)

  if (choosingGoal) {
    const readyCount = phrases.filter(ready).length
    return (
      <section className="screen narrow goal-selection">
        <div className="device-card goal-card">
          <Grille className="grille-strip" />
          <h1 className="large-title">{t('enroll.goalTitle')}</h1>
          <p className="lede-sm">{t('enroll.goalDesc')}</p>
          <div className="goal-options" role="radiogroup" aria-label={t('enroll.goalTitle')}>
            {goalOptions.map((opt) => {
              const isAll = opt === phrases.length && opt !== 10
              const isRecommended = opt === 10
              const isSelected = selectedGoal === opt
              return (
                <button
                  key={opt}
                  type="button"
                  role="radio"
                  aria-checked={isSelected}
                  className={`goal-option-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => setSelectedGoal(opt)}
                >
                  <div className="goal-option-main">
                    <span className="goal-option-count">
                      {isAll
                        ? t('enroll.goalAll', { count: opt })
                        : isRecommended
                        ? t('enroll.goalCountRecommended', { count: opt })
                        : t('enroll.goalCount', { count: opt })}
                    </span>
                  </div>
                  <span className={`goal-radio-circle ${isSelected ? 'checked' : ''}`} />
                </button>
              )
            })}
          </div>
          <Alert error={error} />
          <div className="actions goal-actions">
            <PrimaryButton onClick={confirmGoal} disabled={busy}>
              {t('enroll.goalContinue')}
            </PrimaryButton>
            {readyCount > 0 && (
              <Button onClick={() => setChoosingGoal(false)} disabled={busy}>
                {t('speak.cancel')}
              </Button>
            )}
          </div>
        </div>
      </section>
    )
  }

  const effectiveGoal = user?.phrase_goal || selectedGoal || 10
  const progress = speakProgress(phrases, user?.language, effectiveGoal)
  const targetPhrases = progress.targetPhrases
  const phrase = progress.nextPhrase

  const progressBar = (
    <div className="learned">
      <div className="learned-header">
        <div className="learned-title-group">
          <Label k="device.learned" inline className="learned-label" />
          <span className="learned-count" aria-label={t('enroll.goalReady', { ready: progress.ready, total: progress.total })}>
            {progress.ready} / {progress.total}
          </span>
        </div>
        <button
          type="button"
          className="text-button change-goal-btn"
          onClick={() => {
            setSelectedGoal(progress.total)
            setChoosingGoal(true)
          }}
        >
          {t('enroll.goalChange')}
        </button>
      </div>
      <div
        className="progress-line"
        role="progressbar"
        aria-label={t('enroll.progress')}
        aria-valuemin={0}
        aria-valuemax={progress.total}
        aria-valuenow={progress.ready}
      >
        <div style={{ transform: `scaleX(${progress.total === 0 ? 0 : Math.min(1, progress.ready / progress.total)})` }} />
      </div>
      <p className="learned-subtitle">
        {t('enroll.goalReady', { ready: progress.ready, total: progress.total })}
        {progress.available > progress.total && (
          <span className="learned-context">
            {' '}({t('enroll.goalSubtitle', { selected: progress.total, available: progress.available })})
          </span>
        )}
      </p>
    </div>
  )

  if (progress.open || !phrase) {
    const allDone = progress.ready >= progress.available
    return (
      <section className="screen narrow empty-state">
        {progressBar}
        <h1 className="large-title">{t(allDone ? 'enroll.done' : 'enroll.goalDoneTitle')}</h1>
        <p className="lede-sm">
          {allDone
            ? t('enroll.doneBody')
            : t('enroll.goalDoneDesc', { ready: progress.ready, total: progress.total })}
        </p>
        <div className="actions">
          <PrimaryButton icon="mic" onClick={() => go('/app/speak')}>
            {t('enroll.goSpeak')}
          </PrimaryButton>
          {!allDone && (
            <Button
              onClick={() => {
                setSelectedGoal(progress.total)
                setChoosingGoal(true)
              }}
            >
              {t('enroll.prepareMore')}
            </Button>
          )}
        </div>
      </section>
    )
  }

  function save() {
    run(async () => {
      await api.enroll(phrase.id, blob)
      setPhrases(
        phrases.map((p) =>
          p.id === phrase.id ? { ...p, enrolled: p.enrolled + 1, sample_count: p.sample_count + 1 } : p,
        ),
      )
      setBlob(null)
    })
  }

  const targetIndex = targetPhrases.indexOf(phrase)
  const currentPhraseNum = targetIndex >= 0 ? targetIndex + 1 : progress.ready + 1
  const saved = Math.min(phrase.sample_count, NEEDED)
  const problem = error || recorder.error
  const blobState = recorder.recording ? 'listening' : busy ? 'thinking' : problem ? 'error' : 'rest'

  return (
    <section className="screen enroll">
      <div className="device enroll-device">
        <Grille className="grille-strip" />
        {progressBar}

        <Readout
          blobState={blobState}
          level={recorder.level}
          top={<span className="readout-step">{t('enroll.step', { n: currentPhraseNum, total: progress.total })}</span>}
        >
          <ReadoutRow label="device.say">
            <h1 className="readout-phrase" lang={user?.language}>
              <span className="visually-hidden">{t('enroll.say')}: </span>
              {phrase.text}
            </h1>
            {needsRerecord(phrase) && <p className="readout-note">{t('enroll.rerecord')}</p>}
          </ReadoutRow>
          <ReadoutRow label="device.saved">
            <p className="saved-meter" role="img" aria-label={t('enroll.saved', { n: phrase.sample_count, needed: NEEDED })}>
              {Array.from({ length: NEEDED }, (_, i) => (
                <span key={i} className={`segment ${i < saved ? 'on' : ''}`} />
              ))}
              <span className="saved-count" aria-hidden="true">
                {saved} / {NEEDED}
              </span>
            </p>
          </ReadoutRow>
        </Readout>

        <Alert error={problem} />
        <PushButton recorder={recorder} waiting={busy} disabled={busy} label={blob && t('sun.again')} />
        {blob && !recorder.recording && (
          <div className="actions enroll-actions">
            <Button icon="play" onClick={() => api.play(blob).catch(setError)} disabled={busy}>
              {t('enroll.play')}
            </Button>
            <PrimaryButton onClick={save} disabled={busy}>
              {t('enroll.save')}
            </PrimaryButton>
          </div>
        )}
      </div>
    </section>
  )
}
