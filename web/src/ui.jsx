import { useEffect, useRef, useState } from 'react'

export const MAX_SECONDS = 8
// A second tap this soon after starting is taken as a shaky double tap, not a stop.
const MIN_RECORDING_MS = 700
// Loudness (RMS of the waveform, 0..1). If a recording never gets above this, nothing was said.
// Kept low on purpose: weak voices must never be thrown away as silence.
const SILENCE_RMS = 0.008

export const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches

// A tiny tap on phones that support it (Android); nothing elsewhere.
function haptic() {
  try {
    navigator.vibrate?.(10)
  } catch {
    // vibration blocked: no feedback, nothing else changes
  }
}

// Hindi text with small English underneath.
export function T({ hi, en }) {
  return (
    <>
      <span className="hi">{hi}</span>
      <span className="en" lang="en">
        {en}
      </span>
    </>
  )
}

// What happened and what to do, per kind of failure (see api.js for the server kinds).
const MESSAGES = {
  offline: [
    'Sunn के सर्वर से जुड़ नहीं पाए। देखें कि कंप्यूटर पर सर्वर चल रहा है, फिर दोबारा कोशिश करें।',
    "can't reach the Sunn server. check that it is running on the computer, then try again.",
  ],
  gnani: [
    'पहचान सेवा ने जवाब नहीं दिया। थोड़ी देर रुककर फिर से कोशिश करें।',
    "the speech service didn't answer. wait a moment, then try again.",
  ],
  silent: ['आवाज़ नहीं मिली, फिर से बोलिए।', 'no sound heard, please speak again.'],
  micDenied: [
    'माइक की अनुमति नहीं मिली। ब्राउज़र की सेटिंग में माइक चालू करें, फिर सूरज दबाएँ।',
    'the microphone is blocked. allow it in the browser settings, then tap the sun.',
  ],
  noMic: ['कोई माइक नहीं मिला। माइक जोड़ें, फिर सूरज दबाएँ।', 'no microphone found. connect one, then tap the sun.'],
  insecure: ['माइक के लिए https वाला पता खोलें।', 'open the https address to use the microphone.'],
  playback: ['आवाज़ नहीं चल पाई। वाक्य को फिर से दबाएँ।', "the sound didn't play. tap the phrase again."],
  server: ['कुछ गड़बड़ हुई। फिर से कोशिश करें।', 'something went wrong. please try again.'],
}

export const failure = (kind) => Object.assign(new Error(kind), { kind })

export function Alert({ error }) {
  if (!error) return null
  const [hi, en] = MESSAGES[error.kind] || MESSAGES.server
  return (
    <p className="alert" role="alert">
      <T hi={hi} en={error.kind === 'server' && error.status ? `${en} (${error.message})` : en} />
    </p>
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
              <T hi="रोकने के लिए दबाएँ" en="tap to stop" />
              <span className="seconds">
                {recorder.seconds} / {MAX_SECONDS} सेकंड
              </span>
            </>
          ) : (
            label || <T hi="बोलने के लिए दबाएँ" en="tap to speak" />
          )}
        </span>
      </button>
      {waiting && (
        <p className="listening" role="status">
          <T hi="सुन रहे हैं…" en="listening…" />
        </p>
      )}
    </div>
  )
}
