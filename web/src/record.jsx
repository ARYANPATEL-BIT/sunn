import { useEffect, useRef, useState } from 'react'
import { failure } from './ui/base.jsx'

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
// While recording, `level.current` (0..1) follows the real mic volume; the readout's blob reads
// it every frame, so the voice drives the shape without re-rendering anything.
export function useRecorder(onDone) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState(null)
  const level = useRef(0)
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
    let peak = 0
    let frame

    // Every frame: the loudness of the last ~20ms, for the blob and for silence detection. The
    // blob smooths it itself (attack and release), so this is the raw value.
    function listen() {
      if (analyser && wave) {
        analyser.getFloatTimeDomainData(wave)
        let sum = 0
        for (let i = 0; i < wave.length; i++) sum += wave[i] * wave[i]
        const rms = Math.sqrt(sum / wave.length)
        peak = Math.max(peak, rms)
        level.current = Math.min(1, rms * 8)
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
      level.current = 0
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

  return { recording, seconds, error, toggle, level, reset: () => setError(null) }
}
