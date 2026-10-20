import { ArrowRight, Mic } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useLang } from './i18n/index.jsx'

export const MAX_SECONDS = 8
// A second tap this soon after starting is taken as a shaky double tap, not a stop.
const MIN_RECORDING_MS = 700
// Loudness (RMS of the waveform, 0..1). If a recording never gets above this, nothing was said.
// Kept low on purpose: weak voices must never be thrown away as silence.
const SILENCE_RMS = 0.008

export const reducedMotion = () =>
  matchMedia('(prefers-reduced-motion: reduce)').matches ||
  (typeof document !== 'undefined' && document.documentElement.classList.contains('reduced-motion'))

// A tiny tap on phones that support it (Android); nothing elsewhere.
function haptic() {
  try {
    navigator.vibrate?.(10)
  } catch {
    // vibration blocked: no feedback, nothing else changes
  }
}

// navigate(), with a quick crossfade where the view transitions api exists (not with reduced motion).
export function useGo() {
  const navigate = useNavigate()
  return (to, options) => navigate(to, { viewTransition: !reducedMotion(), ...options })
}

// The "Sunn" wordmark, linking home. Always Latin: it is the name, in both languages.
export function Wordmark() {
  const { t } = useLang()
  return (
    <Link to="/" className="wordmark-link" lang="en" aria-label={t('nav.home')} viewTransition={!reducedMotion()}>
      Sunn
    </Link>
  )
}

export const failure = (kind) => Object.assign(new Error(kind), { kind })

// What happened and what to do, in the current language. A refusal the API explains with a
// code (bad_login, email_taken…) gets its own words; anything else is worded by its kind.
export function errorText({ t, has }, error) {
  if (error.code && has(`error.${error.code}`)) {
    return t(`error.${error.code}`, { minutes: Math.max(1, Math.ceil((error.retryAfter || 0) / 60)) })
  }
  return t(has(`error.${error.kind}`) ? `error.${error.kind}` : 'error.server')
}

export function Alert({ error, id }) {
  const i18n = useLang()
  if (!error) return null
  return (
    <p className="alert" role="alert" id={id}>
      {errorText(i18n, error)}
    </p>
  )
}

// EN / हिं, an outline pill. Switches the whole interface; the user's own phrases stay as stored.
export function LangToggle() {
  const { lang, setLang, t } = useLang()
  return (
    <div className="lang-toggle" role="group" aria-label={t('lang.label')}>
      <button type="button" lang="en" aria-pressed={lang === 'en'} onClick={() => setLang('en')}>
        EN
      </button>
      <span className="lang-slash" aria-hidden="true">
        /
      </span>
      <button type="button" lang="hi" aria-pressed={lang === 'hi'} onClick={() => setLang('hi')}>
        हिं
      </button>
    </div>
  )
}

// The white pill: [mic | label →]. Used for "Start speaking" and every form's submit.
export function Pill({ children, icon: Icon = Mic, arrow = true, className = '', ...props }) {
  return (
    <button type="button" className={`pill ${className}`} {...props}>
      {Icon && (
        <>
          <Icon className="pill-icon" aria-hidden="true" strokeWidth={1.5} />
          <span className="pill-divider" aria-hidden="true" />
        </>
      )}
      <span className="pill-label">{children}</span>
      {arrow && <ArrowRight className="pill-icon" aria-hidden="true" strokeWidth={1.5} />}
    </button>
  )
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

    const rec = new MediaRecorder(stream)
    const chunks = []
    const audio = new AudioContext()
    const analyser = audio.createAnalyser()
    analyser.fftSize = 1024
    audio.createMediaStreamSource(stream).connect(analyser)
    audio.resume()
    const wave = new Float32Array(analyser.fftSize)
    const animate = !reducedMotion()
    let peak = 0
    let level = 0
    let frame

    // Every frame: the loudness of the last ~20ms, for the sun's corona and for silence detection.
    function listen() {
      analyser.getFloatTimeDomainData(wave)
      const rms = Math.sqrt(wave.reduce((sum, s) => sum + s * s, 0) / wave.length)
      const target = Math.min(1, rms * 8)
      peak = Math.max(peak, rms)
      level += (target - level) * (target > level ? 0.5 : 0.08) // rise fast, fall slowly
      if (animate) meter.current?.style.setProperty('--level', level.toFixed(3))
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
      audio.close()
      meter.current?.style.removeProperty('--level')
      haptic()
      setRecording(false)
      if (!done.current) return
      if (peak < SILENCE_RMS) return setError(failure('silent'))
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

  return { recording, seconds, error, toggle, meter }
}

// The record button. Breathes at rest, its corona follows the voice while recording,
// and it slowly dims and brightens while `waiting` for Prisma.
export function Sun({ recorder, onClick = recorder.toggle, waiting, disabled, label, compact }) {
  const { t } = useLang()
  const state = recorder.recording ? 'recording' : waiting ? 'waiting' : ''
  return (
    <div className={`sun-wrap ${compact ? 'compact' : ''}`}>
      <button
        type="button"
        ref={recorder.meter}
        className={`sun ${state}`}
        onClick={onClick}
        disabled={disabled || waiting}
        aria-busy={waiting || undefined}
      >
        <span className="sun-body" aria-hidden="true">
          <span className="corona" />
          <span className="disc" />
        </span>
        <span className="sun-label">
          {recorder.recording ? (
            <>
              {t('sun.stop')}
              <span className="seconds">{t('sun.seconds', { seconds: recorder.seconds, max: MAX_SECONDS })}</span>
            </>
          ) : (
            label || t('sun.tap')
          )}
        </span>
      </button>
      {waiting && (
        <p className="listening" role="status">
          {t('sun.listening')}
        </p>
      )}
    </div>
  )
}
