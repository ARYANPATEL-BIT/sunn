import { useEffect, useMemo, useRef, useState } from 'react'
import * as api from '../../api.js'
import { useAuth } from '../../auth.jsx'
import { useLang } from '../../i18n/index.jsx'
import { useRecorder } from '../../record.jsx'
import { Blob, Icon, PushButton } from '../../ui/index.js'
import { CheckingFeedback } from '../CheckingFeedback.jsx'

function countSyllables(word) {
  if (!word) return 1
  const clean = word.toLowerCase().trim()
  // Devanagari vowel signs and independent vowels
  const devanagari = clean.match(/[\u0904-\u0914\u093e-\u094c\u0902\u0903]/g)
  if (devanagari && devanagari.length > 0) return devanagari.length
  // Latin vowel sequences, discarding trailing silent 'e'
  const normalized = clean.length > 3 ? clean.replace(/e$/, '') : clean
  const latin = normalized.match(/[aeiouy]+/gi)
  if (latin && latin.length > 0) return Math.max(1, latin.length)
  return 1
}

export function SpeakWithMeStep({
  step,
  language = null,
  isKids = false,
  isSmoothOrKids = false,
}) {
  const { user } = useAuth()
  const { t, lang: uiLang } = useLang()
  const mode = step.mode || 'paced'
  const practiceLang = language || step.language || 'hi'

  const title = step.title?.[uiLang] || step.title?.en || t('speakWithMe.title')
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

  // Submode for paced steps: 'paced' (full phrase) or 'word_by_word'
  const [submode, setSubmode] = useState('paced')

  // Playback and Highlight state
  const [playing, setPlaying] = useState(false)
  const [audioLoading, setAudioLoading] = useState(false)
  const [audioError, setAudioError] = useState(null)
  const [activeWordIndex, setActiveWordIndex] = useState(-1)
  const [recordMeToo, setRecordMeToo] = useState(false)
  const [echoPhase, setEchoPhase] = useState('idle') // idle | sunn_speaking | pause | your_turn

  // Recording and Checking state
  const [recordedBlob, setRecordedBlob] = useState(null)
  const [attemptResult, setAttemptResult] = useState(null)
  const [checking, setChecking] = useState(false)
  const [checkingError, setCheckingError] = useState(null)
  const [checksLeft, setChecksLeft] = useState(20)

  const audioRef = useRef(null)
  const audioBlobRef = useRef(null)
  const audioUrlRef = useRef(null)
  const wordLoopAbortRef = useRef(false)
  const animFrameRef = useRef(null)
  const startTimeRef = useRef(0)
  const elapsedOffsetRef = useRef(0)
  const totalDurationRef = useRef(2.5)

  const recorder = useRecorder(async (blob) => {
    setRecordedBlob(blob)
    setAttemptResult(null)
    setCheckingError(null)
    if (user) {
      try {
        await api.postTrainingsAttempt(
          blob,
          step.id,
          null,
          false,
          step.text,
          practiceLang,
        )
      } catch {
        // Non-blocking background attempt recording
      }
    }
  })

  // Cleanup on step or text change or unmount
  useEffect(() => {
    wordLoopAbortRef.current = true
    api.stopAudio()
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current)
      audioUrlRef.current = null
    }
    audioBlobRef.current = null
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current)
      animFrameRef.current = null
    }
    setPlaying(false)
    setAudioLoading(false)
    setAudioError(null)
    setActiveWordIndex(-1)
    setEchoPhase('idle')
    setRecordedBlob(null)
    setAttemptResult(null)
    setChecking(false)
    setCheckingError(null)
    elapsedOffsetRef.current = 0
    setWpm(step.pace_wpm?.[0] || 40)
  }, [step.id, step.text])

  // Helper to compute word highlight based on elapsed seconds
  const updateHighlight = (elapsedSec, totalDuration) => {
    if (totalDuration <= 0) return true
    const progress = Math.min(1.0, Math.max(0.0, elapsedSec / totalDuration))
    if (progress >= 1.0) {
      setActiveWordIndex(words.length)
      return true
    }
    let cumulative = 0
    for (let i = 0; i < words.length; i++) {
      const startProg = cumulative / totalSyllables
      cumulative += syllables[i]
      const endProg = cumulative / totalSyllables
      if (progress >= startProg && progress < endProg) {
        setActiveWordIndex(i)
        return false
      }
    }
    setActiveWordIndex(words.length)
    return true
  }

  // Choral and Paced animation tick loop synchronized with audio playback
  const startHighlightLoop = (audioEl = null, baseDuration = 2.5) => {
    totalDurationRef.current = baseDuration
    startTimeRef.current = performance.now()
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current)
      animFrameRef.current = null
    }

    const tick = () => {
      let elapsed
      let dur = totalDurationRef.current
      if (audioEl && audioEl.duration && audioEl.duration > 0.1) {
        elapsed = audioEl.currentTime
        dur = audioEl.duration
        if (audioEl.ended || elapsed >= dur) {
          setActiveWordIndex(words.length)
          setPlaying(false)
          elapsedOffsetRef.current = 0
          if (recorder.recording && recordMeToo) {
            recorder.toggle()
          }
          return
        }
      } else {
        const now = performance.now()
        elapsed = elapsedOffsetRef.current + (now - startTimeRef.current) / 1000
        if (elapsed >= dur) {
          setActiveWordIndex(words.length)
          setPlaying(false)
          elapsedOffsetRef.current = 0
          if (recorder.recording && recordMeToo) {
            recorder.toggle()
          }
          return
        }
      }

      updateHighlight(elapsed, dur)
      animFrameRef.current = requestAnimationFrame(tick)
    }

    animFrameRef.current = requestAnimationFrame(tick)
  }

  // Load audio blob (from step audio_key or dynamic TTS synthesize)
  const loadAudio = async () => {
    if (audioBlobRef.current) return audioBlobRef.current
    let blob = null
    if (step.audio_key) {
      blob = await api.fetchAudioBlob(step.audio_key)
    } else {
      blob = await api.speak(step.text, practiceLang)
    }
    if (blob) {
      audioBlobRef.current = blob
      const url = URL.createObjectURL(blob)
      audioUrlRef.current = url
      const audio = new Audio(url)
      audioRef.current = audio
    }
    return blob
  }

  // --- PACED MODE: FULL PHRASE PLAYBACK ---
  const handlePacedFullPhrasePlay = async () => {
    if (playing) {
      wordLoopAbortRef.current = true
      api.stopAudio()
      if (audioRef.current) {
        audioRef.current.pause()
      } else {
        elapsedOffsetRef.current += (performance.now() - startTimeRef.current) / 1000
      }
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current)
        animFrameRef.current = null
      }
      setPlaying(false)
      if (recorder.recording && recordMeToo) recorder.toggle()
      return
    }

    setPlaying(true)
    setAudioError(null)
    wordLoopAbortRef.current = false

    let audio = audioRef.current
    if (!audio) {
      setAudioLoading(true)
      try {
        await loadAudio()
        audio = audioRef.current
      } catch (err) {
        setAudioError(err?.message || 'Playback error')
        audio = null
      } finally {
        setAudioLoading(false)
      }
    }

    if (activeWordIndex >= words.length || activeWordIndex === -1) {
      elapsedOffsetRef.current = 0
      setActiveWordIndex(0)
      if (audio) audio.currentTime = 0
    }

    if (audio) {
      const baseDuration = audio.duration && audio.duration > 0.1 ? audio.duration : Math.max(2.0, words.length * 0.7)
      const baseWpm = Math.max(25, Math.round((words.length * 60) / baseDuration))
      const rate = Math.max(0.5, Math.min(2.0, wpm / baseWpm))
      audio.playbackRate = rate
      audio.onended = () => {
        setPlaying(false)
        setActiveWordIndex(words.length)
        if (recorder.recording && recordMeToo) {
          recorder.toggle()
        }
      }
      try {
        await audio.play()
      } catch {
        // Non-blocking
      }
      startHighlightLoop(audio, baseDuration)
    } else {
      // Fallback synthesis
      const targetDuration = Math.max(1.5, (words.length * 60) / wpm)
      api.say(step.text, { fallback: true, language: practiceLang })
        .then(() => {
          setPlaying(false)
          setActiveWordIndex(words.length)
          if (recorder.recording && recordMeToo) recorder.toggle()
        })
        .catch(() => {})
      startHighlightLoop(null, targetDuration)
    }

    if (recordMeToo && !recorder.recording) {
      recorder.toggle()
    }
  }

  // --- PACED MODE: WORD BY WORD PLAYBACK ---
  const handleWordByWordPlay = async () => {
    if (playing) {
      wordLoopAbortRef.current = true
      api.stopAudio()
      setPlaying(false)
      if (recorder.recording && recordMeToo) recorder.toggle()
      return
    }

    setPlaying(true)
    setAudioError(null)
    wordLoopAbortRef.current = false

    if (recordMeToo && !recorder.recording) {
      recorder.toggle()
    }

    const pauseMs = Math.max(250, Math.round((60000 / wpm) * 0.45))
    const startIndex = activeWordIndex >= words.length || activeWordIndex === -1 ? 0 : activeWordIndex

    for (let i = startIndex; i < words.length; i++) {
      if (wordLoopAbortRef.current) break
      setActiveWordIndex(i)
      try {
        await api.say(words[i], { fallback: true, language: practiceLang })
      } catch {
        // Non-blocking
      }
      if (wordLoopAbortRef.current) break
      await new Promise((resolve) => setTimeout(resolve, pauseMs))
    }

    if (!wordLoopAbortRef.current) {
      setPlaying(false)
      setActiveWordIndex(words.length)
      if (recorder.recording && recordMeToo) {
        recorder.toggle()
      }
    }
  }

  // Combined toggle play depending on submode
  const handlePacedTogglePlay = () => {
    if (submode === 'word_by_word') {
      handleWordByWordPlay()
    } else {
      handlePacedFullPhrasePlay()
    }
  }

  // --- CHORAL MODE PLAYBACK ---
  const handleChoralTogglePlay = async () => {
    if (playing) {
      if (audioRef.current) audioRef.current.pause()
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      setPlaying(false)
      if (recorder.recording && recordMeToo) recorder.toggle()
      return
    }

    setPlaying(true)
    setAudioError(null)
    let audio = audioRef.current
    if (!audio) {
      setAudioLoading(true)
      try {
        await loadAudio()
        audio = audioRef.current
      } catch (err) {
        setAudioError(err?.message || 'Playback error')
        audio = null
      } finally {
        setAudioLoading(false)
      }
    }

    if (activeWordIndex >= words.length || activeWordIndex === -1) {
      elapsedOffsetRef.current = 0
      setActiveWordIndex(0)
      if (audio) audio.currentTime = 0
    }

    const duration = audio?.duration && audio.duration > 0.5 ? audio.duration : Math.max(2.5, words.length * 0.75)
    if (audio) {
      audio.onended = () => {
        setPlaying(false)
        setActiveWordIndex(words.length)
        if (recorder.recording && recordMeToo) recorder.toggle()
      }
      try {
        await audio.play()
      } catch {
        // Non-blocking
      }
      startHighlightLoop(audio, duration)
    } else {
      api.say(step.text, { fallback: true, language: practiceLang })
        .then(() => {
          setPlaying(false)
          setActiveWordIndex(words.length)
          if (recorder.recording && recordMeToo) recorder.toggle()
        })
        .catch(() => {})
      startHighlightLoop(null, duration)
    }

    if (recordMeToo && !recorder.recording) {
      recorder.toggle()
    }
  }

  // Click on a single word to speak it
  const handleWordClick = async (idx, word) => {
    if (playing) {
      wordLoopAbortRef.current = true
      api.stopAudio()
      if (audioRef.current) audioRef.current.pause()
      setPlaying(false)
    }
    setActiveWordIndex(idx)
    try {
      await api.say(word, { fallback: true, language: practiceLang })
    } catch {
      // Non-blocking
    }
  }

  // --- EXPLICIT RECORDING HANDLER ---
  const handleToggleRecord = () => {
    if (playing) {
      wordLoopAbortRef.current = true
      api.stopAudio()
      if (audioRef.current) audioRef.current.pause()
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      setPlaying(false)
    }
    recorder.toggle()
  }

  // --- RESTART HANDLER ---
  const handleRestart = () => {
    wordLoopAbortRef.current = true
    api.stopAudio()
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current)
      animFrameRef.current = null
    }
    if (recorder.recording) {
      recorder.toggle()
    }
    setPlaying(false)
    setActiveWordIndex(-1)
    elapsedOffsetRef.current = 0
    setRecordedBlob(null)
    setAttemptResult(null)
    setCheckingError(null)
  }

  // --- ECHO MODE WORKFLOW ---
  const handleEchoListen = async () => {
    setEchoPhase('sunn_speaking')
    setAudioError(null)
    try {
      if (step.audio_key) {
        await api.playAudioKey(step.audio_key)
      } else {
        await api.say(step.text, { fallback: true, language: practiceLang })
      }
    } catch (err) {
      setAudioError(err?.message || 'Playback error')
    }
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
    setCheckingError(null)
  }

  // --- CHECKING HANDLERS ---
  const handleCheck = async () => {
    if (!recordedBlob) return
    setChecking(true)
    setCheckingError(null)
    try {
      const res = await api.postTrainingsAttempt(
        recordedBlob,
        step.id,
        null,
        true,
        step.text,
        practiceLang,
      )
      setAttemptResult(res)
      if (res?.checks_left_today != null) {
        setChecksLeft(res.checks_left_today)
      }
    } catch (err) {
      const msg = err?.message || err?.detail || t('check.errorCouldNotCheck')
      setCheckingError(msg)
    } finally {
      setChecking(false)
    }
  }

  const handlePractiseAgain = () => {
    setRecordedBlob(null)
    setAttemptResult(null)
    setCheckingError(null)
    setActiveWordIndex(-1)
    if (mode === 'echo') {
      setEchoPhase('idle')
    }
  }

  return (
    <div className={`step-container step-speak-with-me ${isKids ? 'is-kids' : ''}`}>
      <div className="step-card">
        {/* Header Row: Title and Mode Badge */}
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
                  lang={practiceLang}
                  onClick={() => handleWordClick(idx, word)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      handleWordClick(idx, word)
                    }
                  }}
                  title={word}
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

        {/* Recording voice level Blob when active */}
        {recorder.recording && (
          <div className="speak-blob-stage" aria-hidden="true">
            <Blob state="listening" level={recorder.level} />
          </div>
        )}

        {/* Shadowing active status */}
        {recordMeToo && playing && (
          <div className="shadowing-active-badge" role="status">
            <Icon name="mic" />
            <span>{t('speakWithMe.shadowingActive')}</span>
          </div>
        )}

        {/* Recorded status notice */}
        {recordedBlob && !recorder.recording && (
          <div className="recorded-status-badge" role="status">
            <Icon name="checkCircle" />
            <span>{t('speakWithMe.recordingCaptured')}</span>
          </div>
        )}

        {/* Microphone Error Alert */}
        {recorder.error && (
          <div className="recorder-error-alert" role="alert">
            <Icon name="alert" />
            <span>{recorder.error.message || t('check.errorCouldNotCheck')}</span>
          </div>
        )}

        {/* Audio Playback Error Alert */}
        {audioError && (
          <div className="recorder-error-alert" role="alert">
            <Icon name="alert" />
            <span>{audioError}</span>
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
                disabled={audioLoading}
                aria-label={playing ? t('step.pause') : t('step.play')}
              >
                <Icon name={playing ? 'pause' : 'play'} />
                <span>{playing ? t('step.pause') : t('step.play')}</span>
              </button>

              <button
                type="button"
                className={`button speak-control-btn record-toggle-btn ${recorder.recording ? 'recording' : ''}`}
                onClick={handleToggleRecord}
                aria-label={recorder.recording ? t('speakWithMe.stopRecordAction') : t('speakWithMe.recordAction')}
              >
                <Icon name={recorder.recording ? 'stop' : 'mic'} />
                <span>{recorder.recording ? t('speakWithMe.stopRecordAction') : t('speakWithMe.recordAction')}</span>
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
              <span>{t('speakWithMe.shadowingNote')}</span>
            </label>
          </div>
        )}

        {mode === 'paced' && (
          <div className="speak-mode-controls paced-controls">
            {/* Practice submode selector: Full phrase vs Word-by-word */}
            <div className="practice-submode-row" role="radiogroup" aria-label="Practice submode">
              <button
                type="button"
                role="radio"
                aria-checked={submode === 'paced'}
                className={`chip submode-chip ${submode === 'paced' ? 'active selected' : ''}`}
                onClick={() => {
                  setSubmode('paced')
                  if (playing) handleRestart()
                }}
              >
                {t('speakWithMe.fullPhrase')}
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={submode === 'word_by_word'}
                className={`chip submode-chip ${submode === 'word_by_word' ? 'active selected' : ''}`}
                onClick={() => {
                  setSubmode('word_by_word')
                  if (playing) handleRestart()
                }}
              >
                {t('speakWithMe.wordByWord')}
              </button>
            </div>

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
                  onChange={(e) => {
                    const newWpm = Number(e.target.value)
                    setWpm(newWpm)
                    if (audioRef.current && playing) {
                      const baseDuration = audioRef.current.duration || 2.0
                      const baseWpm = Math.max(25, Math.round((words.length * 60) / baseDuration))
                      audioRef.current.playbackRate = Math.max(0.5, Math.min(2.0, newWpm / baseWpm))
                    }
                  }}
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
                disabled={audioLoading}
                aria-label={playing ? t('step.pause') : t('step.play')}
              >
                <Icon name={playing ? 'pause' : 'play'} />
                <span>{audioLoading ? '...' : playing ? t('step.pause') : t('step.play')}</span>
              </button>

              <button
                type="button"
                className={`button speak-control-btn record-toggle-btn ${recorder.recording ? 'recording' : ''}`}
                onClick={handleToggleRecord}
                aria-label={recorder.recording ? t('speakWithMe.stopRecordAction') : t('speakWithMe.recordAction')}
              >
                <Icon name={recorder.recording ? 'stop' : 'mic'} />
                <span>{recorder.recording ? t('speakWithMe.stopRecordAction') : t('speakWithMe.recordAction')}</span>
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
              <span>{t('speakWithMe.shadowingNote')}</span>
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
          error={checkingError}
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
