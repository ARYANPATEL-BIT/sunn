import { Mic, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useLang } from './i18n/index.jsx'
import { failure, reducedMotion } from './ui.jsx'

export const MAX_SECONDS = 8
// A second tap this soon after starting is taken as a shaky double tap, not a stop.
const MIN_RECORDING_MS = 700
// Loudness (RMS of the waveform, 0..1). If a recording never gets above this, nothing was said.
// Kept low on purpose: weak voices must never be thrown away as silence.
const SILENCE_RMS = 0.008

// A tiny tap on phones that support it (Android); nothing elsewhere.
function haptic() {
  try {
    navigator.vibrate?.(10)
  } catch {
    // vibration blocked: no feedback, nothing else changes
  }
}

// Tap to start, tap to stop, auto-stop after MAX_SECONDS. onDone gets the recorded blob.
// While recording, the element in `meter` gets a --level (0..1) that follows the real mic volume.
export function useRecorder(onDone) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState(null)
  const meter = useRef(null)
  const recorder = useRef(null)
  const startedAt = useRef(0)
  const starting = useRef(false)
  const done = useRef(onDone)
  done.current = onDone

  // Leaving the screen mid-recording discards the recording instead of uploading it.
  useEffect(
    () => () => {
      done.current = null
      stop()
    },
    [],
  )

  function stop() {
    if (recorder.current?.state === 'recording') recorder.current.stop()
  }

  async function start() {
    setError(null)
    if (!navigator.mediaDevices?.getUserMedia) return setError(failure('insecure'))
    starting.current = true
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      return setError(failure(e.name === 'NotFoundError' ? 'noMic' : 'micDenied'))
    } finally {
      starting.current = false
    }
    if (!done.current) return stream.getTracks().forEach((track) => track.stop()) // left the screen meanwhile

    if (typeof window !== 'undefined' && typeof window.MediaRecorder === 'undefined') {
      stream.getTracks().forEach((track) => track.stop())
      return setError(failure('unsupported'))
    }

    const rec = new MediaRecorder(stream)
    const chunks = []
    const AudioCtx = window.AudioContext || window.webkitAudioContext
    let audio = null
    let analyser = null
    if (AudioCtx) {
      try {
        audio = new AudioCtx()
        analyser = audio.createAnalyser()
        analyser.fftSize = 1024
        audio.createMediaStreamSource(stream).connect(analyser)
        audio.resume()
      } catch {
        audio = null
        analyser = null
      }
    }
    const wave = analyser ? new Float32Array(analyser.fftSize) : null
    const animate = !reducedMotion()
    let peak = 0
    let level = 0
    let frame

    // Every frame: the loudness of the last ~20ms, for the record button's ring and for silence detection.
    function listen() {
      if (analyser && wave) {
        analyser.getFloatTimeDomainData(wave)
        const rms = Math.sqrt(wave.reduce((sum, s) => sum + s * s, 0) / wave.length)
        const target = Math.min(1, rms * 8)
        peak = Math.max(peak, rms)
        level += (target - level) * (target > level ? 0.5 : 0.08) // rise fast, fall slowly
        if (animate) meter.current?.style.setProperty('--level', level.toFixed(3))
      }
      frame = requestAnimationFrame(listen)
    }

    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt.current) / 1000)
      setSeconds(elapsed)
      if (elapsed >= MAX_SECONDS) stop()
    }, 200)
    rec.ondataavailable = (e) => chunks.push(e.data)
    rec.onstop = () => {
      cancelAnimationFrame(frame)
      clearInterval(timer)
      stream.getTracks().forEach((track) => track.stop())
      try {
        audio?.close()
      } catch {
        // Non-blocking cleanup
      }
      meter.current?.style.removeProperty('--level')
      haptic()
      setRecording(false)
      if (!done.current) return
      if (!chunks.length || chunks.every((c) => c.size === 0) || peak < SILENCE_RMS) {
        return setError(failure('silent'))
      }
      done.current(new Blob(chunks, { type: rec.mimeType }))
    }
    recorder.current = rec
    startedAt.current = Date.now()
    rec.start()
    haptic()
    setSeconds(0)
    setRecording(true)
    listen()
  }

  function toggle() {
    if (starting.current) return
    if (recorder.current?.state !== 'recording') start()
    else if (Date.now() - startedAt.current >= MIN_RECORDING_MS) stop()
  }

  return { recording, seconds, error, toggle, meter, reset: () => setError(null) }
}

// The circle itself, shared with the landing page's example: black in light, white in dark,
// red while recording with a ring behind it that follows --level.
export function RecordCircle({ state }) {
  return (
    <span className="record-visual" aria-hidden="true">
      <span className="record-ring" />
      <span className="record-circle">
        {state === 'recording' ? (
          <Square className="record-icon" fill="currentColor" strokeWidth={0} />
        ) : (
          <Mic className="record-icon" strokeWidth={1.5} />
        )}
      </span>
    </span>
  )
}

// The record button: the circle and what tapping it does. It dims while `waiting` for Prisma.
export function RecordButton({ recorder, onClick = recorder.toggle, waiting, disabled, label, compact }) {
  const { t } = useLang()
  const state = recorder.recording ? 'recording' : waiting ? 'waiting' : 'idle'
  return (
    <div className={`record-wrap ${compact ? 'compact' : ''}`}>
      <button
        type="button"
        ref={recorder.meter}
        className={`record ${state}`}
        onClick={onClick}
        disabled={disabled || waiting}
        aria-busy={waiting || undefined}
      >
        <RecordCircle state={state} />
        <span className="record-label">
          {recorder.recording ? (
            <>
              {t('sun.stop')}
              <span className="record-seconds">
                {t('sun.seconds', { seconds: recorder.seconds, max: MAX_SECONDS })}
              </span>
            </>
          ) : (
            label || t('sun.tap')
          )}
        </span>
      </button>
      {waiting && (
        <p className="record-status" role="status">
          {t('sun.listening')}
        </p>
      )}
    </div>
  )
}
