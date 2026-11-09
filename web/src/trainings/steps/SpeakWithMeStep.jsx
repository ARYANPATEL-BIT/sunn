import { useEffect, useMemo, useRef, useState } from 'react'
import * as api from '../../api.js'
import { useAuth } from '../../auth.jsx'
import { useLang } from '../../i18n/index.jsx'
import { useRecorder } from '../../record.jsx'
import { Blob, Icon, PushButton } from '../../ui/index.js'
import { CheckingFeedback } from '../CheckingFeedback.jsx'

function countSyllables(word) {
  if (!word) return 1
  // Devanagari vowel signs & independent vowels
  const devanagari = word.match(/[\u0904-\u0914\u093e-\u094c\u0902\u0903]/g)
  if (devanagari && devanagari.length > 0) return devanagari.length
  // Latin vowel sequences
  const latin = word.match(/[aeiouy]+/gi)
  if (latin && latin.length > 0) return Math.max(1, latin.length)
  return 1
}

export function SpeakWithMeStep({
  step,
  isKids = false,
  isSmoothOrKids = false,
}) {
  const { user } = useAuth()
  const { t, lang } = useLang()
  const mode = step.mode || 'choral'

  const title = step.title?.[lang] || step.title?.en || t('speakWithMe.title')
  const modeKey =
    mode === 'choral'
      ? 'speakWithMe.choral'
      : mode === 'echo'
        ? 'speakWithMe.echo'
        : 'speakWithMe.paced'

  const modeDescKey =
    mode === 'choral'
      ? 'speakWithMe.choralDesc'
      : mode === 'echo'
        ? 'speakWithMe.echoDesc'
        : 'speakWithMe.pacedDesc'

  // Words list and syllable weights
  const words = useMemo(() => {
    return (step.text || '').trim().split(/\s+/).filter(Boolean)
  }, [step.text])

  const syllables = useMemo(() => {
    return words.map((w) => countSyllables(w))
  }, [words])

  const totalSyllables = useMemo(() => {
    return syllables.reduce((a, b) => a + b, 0) || 1
  }, [syllables])

  // Paced mode pace_wpm range
  const minWpm = step.pace_wpm?.[0] || 40
  const maxWpm = step.pace_wpm?.[1] || 100
  const [wpm, setWpm] = useState(minWpm)

  // Playback & Highlight state
  const [playing, setPlaying] = useState(false)
  const [activeWordIndex, setActiveWordIndex] = useState(-1)
  const [recordMeToo, setRecordMeToo] = useState(false)
  const [echoPhase, setEchoPhase] = useState('idle') // idle | sunn_speaking | pause | your_turn

  // Recording & Checking state
  const [recordedBlob, setRecordedBlob] = useState(null)
  const [attemptResult, setAttemptResult] = useState(null)
  const [checking, setChecking] = useState(false)
  const [checksLeft, setChecksLeft] = useState(24)

  const audioRef = useRef(null)
  const animFrameRef = useRef(null)
  const startTimeRef = useRef(0)
  const elapsedOffsetRef = useRef(0)
  const totalDurationRef = useRef(2.5)

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

  // Cleanup on step change or unmount
  useEffect(() => {
    api.stopAudio()
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current)
      animFrameRef.current = null
    }
    setPlaying(false)
    setActiveWordIndex(-1)
    setEchoPhase('idle')
    setRecordedBlob(null)
    setAttemptResult(null)
    setChecking(false)
    elapsedOffsetRef.current = 0
    setWpm(step.pace_wpm?.[0] || 40)
  }, [step.id])

  // Helper to compute word highlight based on elapsed seconds
  const updateHighlight = (elapsedSec, totalDuration) => {
    if (elapsedSec >= totalDuration) {
      setActiveWordIndex(words.length) // All words passed
      return true
    }
    let cumulative = 0
    for (let i = 0; i < words.length; i++) {
      const start = (cumulative / totalSyllables) * totalDuration
      cumulative += syllables[i]
      const end = (cumulative / totalSyllables) * totalDuration
      if (elapsedSec >= start && elapsedSec < end) {
        setActiveWordIndex(i)
        return false
      }
    }
    setActiveWordIndex(words.length)
    return true
  }

  // Choral & Paced animation tick loop
  const startHighlightLoop = (audioEl = null, targetDuration = 2.5) => {
    totalDurationRef.current = targetDuration
    startTimeRef.current = performance.now()

    const tick = () => {
      let elapsed
      if (audioEl && audioEl.duration > 1.2) {
        elapsed = audioEl.currentTime
      } else {
        const now = performance.now()
        elapsed = elapsedOffsetRef.current + (now - startTimeRef.current) / 1000
      }

      const done = updateHighlight(elapsed, totalDurationRef.current)
      if (done) {
        setPlaying(false)
        elapsedOffsetRef.current = 0
        if (recorder.recording) {
          recorder.toggle()
        }
      } else {
        animFrameRef.current = requestAnimationFrame(tick)
      }
    }

    animFrameRef.current = requestAnimationFrame(tick)
  }

  // --- CHORAL MODE PLAYBACK ---
  const handleChoralTogglePlay = async () => {
    if (playing) {
      // Pause
      if (audioRef.current) audioRef.current.pause()
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      setPlaying(false)
      if (recorder.recording) recorder.toggle()
      return
    }

    // Play
    setPlaying(true)
    let audio = audioRef.current
    if (!audio && step.audio_key) {
      try {
        const blob = await api.fetchAudioBlob(step.audio_key)
        if (blob) {
          const url = URL.createObjectURL(blob)
          audio = new Audio(url)
          audioRef.current = audio
        }
      } catch {
        // Fallback to synthetic timing if audio fails
        audio = null
      }
    }

    // Reset if previously completed
    if (activeWordIndex >= words.length || activeWordIndex === -1) {
      elapsedOffsetRef.current = 0
      setActiveWordIndex(0)
      if (audio) audio.currentTime = 0
    }

    let dur = audio?.duration && audio.duration > 1.2 ? audio.duration : Math.max(2.5, words.length * 0.75)

    if (audio) {
      audio.onended = () => {
        // End of audio
      }
      try {
        await audio.play()
      } catch {
        // Non-blocking playback
      }
    }

    if (recordMeToo && !recorder.recording) {
      recorder.toggle()
    }

    startHighlightLoop(audio, dur)
  }

  // --- PACED MODE PLAYBACK ---
  const handlePacedTogglePlay = () => {
    if (playing) {
      // Pause
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      setPlaying(false)
      if (recorder.recording) recorder.toggle()
      return
    }

    // Play
    setPlaying(true)
    if (activeWordIndex >= words.length || activeWordIndex === -1) {
      elapsedOffsetRef.current = 0
      setActiveWordIndex(0)
    }

    const duration = (words.length * 60) / wpm
    if (recordMeToo && !recorder.recording) {
      recorder.toggle()
    }

    startHighlightLoop(null, duration)
  }

  // --- RESTART HANDLER (Choral / Paced) ---
  const handleRestart = () => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
    if (recorder.recording) {
      recorder.toggle()
    }
    setPlaying(false)
    setActiveWordIndex(-1)
    elapsedOffsetRef.current = 0
    setRecordedBlob(null)
    setAttemptResult(null)
  }

  // --- ECHO MODE WORKFLOW ---
  const handleEchoListen = async () => {
    if (!step.audio_key) return
    setEchoPhase('sunn_speaking')
    try {
      await api.playAudioKey(step.audio_key)
    } catch {
      // Non-blocking
    }
    // Pause briefly then your turn
    setEchoPhase('pause')
    setTimeout(() => {
      setEchoPhase('your_turn')
    }, 500)
  }

  const handleEchoRestart = () => {
    api.stopAudio()
    setEchoPhase('idle')
    setRecordedBlob(null)
    setAttemptResult(null)
  }

  // --- CHECKING HANDLERS ---
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
    setActiveWordIndex(-1)
    if (mode === 'echo') {
      setEchoPhase('idle')
    }
  }

  return (
    <div className={`step-container step-speak-with-me ${isKids ? 'is-kids' : ''}`}>
      <div className="step-card">
        {/* Header Row: Title & Mode Badge */}
        <div className="step-header-row">
          <h2 className="step-main-title">{title}</h2>
          <span className="step-mode-badge">
            {t('speakWithMe.mode', { mode: t(modeKey) })}
          </span>
        </div>

        {/* Mode guidance */}
        <p className="step-guidance-subtext">{t(modeDescKey)}</p>

        {/* Echo Mode Phase Banner */}
        {mode === 'echo' && echoPhase !== 'idle' && (
          <div
            className={`echo-phase-banner ${echoPhase}`}
            role="status"
            aria-live="polite"
          >
            {echoPhase === 'sunn_speaking' && (
              <>
                <Icon name="volume" />
                <span>{t('speakWithMe.sunnSpeaking')}</span>
              </>
            )}
            {echoPhase === 'pause' && (
              <span className="echo-pause-dots">...</span>
            )}
            {echoPhase === 'your_turn' && (
              <>
                <Icon name="mic" />
                <span>{t('speakWithMe.yourTurn')}</span>
              </>
            )}
          </div>
        )}

        {/* Big Phrase Display with Word Lighting */}
        <div className="phrase-hero-stage">
          <div className="speak-words-display" aria-label={step.text}>
            {words.map((word, idx) => {
              let stateClass = 'upcoming'
              if (activeWordIndex === -1) {
                stateClass = 'rest'
              } else if (idx === activeWordIndex) {
                stateClass = 'current'
              } else if (idx < activeWordIndex) {
                stateClass = 'past'
              }
              return (
                <span
                  key={idx}
                  className={`word-span ${stateClass}`}
                  lang="hi"
                >
                  {word}
                </span>
              )
            })}
          </div>
          {step.latin && <p className="phrase-latin-text">{step.latin}</p>}
          {step.meaning_en && (
            <p className="phrase-meaning-text">{step.meaning_en}</p>
          )}
        </div>

        {/* Recording mic voice level Blob */}
        {recorder.recording && (
          <div className="speak-blob-stage" aria-hidden="true">
            <Blob state="listening" level={recorder.level} />
          </div>
        )}

        {/* Controls according to mode */}
        {mode === 'choral' && (
          <div className="speak-mode-controls choral-controls">
            <div className="speak-main-buttons">
              <button
                type="button"
                className="button speak-control-btn play-pause-btn"
                onClick={handleChoralTogglePlay}
                aria-label={playing ? t('step.pause') : t('step.play')}
              >
                <Icon name={playing ? 'pause' : 'play'} />
                <span>{playing ? t('step.pause') : t('step.play')}</span>
              </button>

              <button
                type="button"
                className="button speak-control-btn restart-btn"
                onClick={handleRestart}
                aria-label={t('speakWithMe.restart')}
              >
                <Icon name="rotate" />
                <span>{t('speakWithMe.restart')}</span>
              </button>
            </div>

            <label className="record-me-toggle">
              <input
                type="checkbox"
                checked={recordMeToo}
                onChange={(e) => setRecordMeToo(e.target.checked)}
              />
              <span>{t('speakWithMe.recordMeToo')}</span>
            </label>
          </div>
        )}

        {mode === 'paced' && (
          <div className="speak-mode-controls paced-controls">
            {/* Speed slider */}
            <div className="pace-slider-box">
              <span className="pace-slider-label">{t('speakWithMe.paceSlider')}</span>
              <div className="pace-slider-row">
                <span className="pace-bound-text">{t('speakWithMe.slower')}</span>
                <input
                  type="range"
                  min={minWpm}
                  max={maxWpm}
                  step={5}
                  value={wpm}
                  onChange={(e) => setWpm(Number(e.target.value))}
                  aria-label={t('speakWithMe.paceSlider')}
                  className="pace-range-input"
                />
                <span className="pace-bound-text">{t('speakWithMe.faster')}</span>
              </div>
              <span className="pace-current-wpm">
                {t('speakWithMe.wpmLabel', { wpm })}
              </span>
            </div>

            <div className="speak-main-buttons">
              <button
                type="button"
                className="button speak-control-btn play-pause-btn"
                onClick={handlePacedTogglePlay}
                aria-label={playing ? t('step.pause') : t('step.play')}
              >
                <Icon name={playing ? 'pause' : 'play'} />
                <span>{playing ? t('step.pause') : t('step.play')}</span>
              </button>

              <button
                type="button"
                className="button speak-control-btn restart-btn"
                onClick={handleRestart}
                aria-label={t('speakWithMe.restart')}
              >
                <Icon name="rotate" />
                <span>{t('speakWithMe.restart')}</span>
              </button>
            </div>

            <label className="record-me-toggle">
              <input
                type="checkbox"
                checked={recordMeToo}
                onChange={(e) => setRecordMeToo(e.target.checked)}
              />
              <span>{t('speakWithMe.recordMeToo')}</span>
            </label>
          </div>
        )}

        {mode === 'echo' && (
          <div className="speak-mode-controls echo-controls">
            {echoPhase !== 'your_turn' ? (
              <div className="speak-main-buttons">
                <button
                  type="button"
                  className="button speak-control-btn play-pause-btn"
                  onClick={handleEchoListen}
                  disabled={echoPhase === 'sunn_speaking'}
                  aria-label={t('readAloud.listenSunn')}
                >
                  <Icon name={echoPhase === 'sunn_speaking' ? 'volume' : 'play'} />
                  <span>
                    {echoPhase === 'sunn_speaking'
                      ? t('step.playing')
                      : t('readAloud.listenSunn')}
                  </span>
                </button>
              </div>
            ) : (
              <div className="echo-record-seat">
                <div className="record-seat">
                  <PushButton recorder={recorder} />
                </div>
                <button
                  type="button"
                  className="button small echo-restart-btn"
                  onClick={handleEchoRestart}
                >
                  <Icon name="rotate" />
                  <span>{t('speakWithMe.restart')}</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Checking Feedback Stage */}
        <CheckingFeedback
          hasRecording={Boolean(recordedBlob)}
          attempt={attemptResult}
          checking={checking}
          onCheck={handleCheck}
          onPractiseAgain={handlePractiseAgain}
          feedbackType={step.feedback || 'pace'}
          isKids={isKids}
          isSmoothOrKids={isSmoothOrKids}
          checksLeftToday={checksLeft}
        />
      </div>
    </div>
  )
}
