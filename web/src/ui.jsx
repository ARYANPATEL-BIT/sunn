import { useEffect, useRef, useState } from 'react'

export const MAX_SECONDS = 8
// A second tap this soon after starting is taken as a shaky double tap, not a stop.
const MIN_RECORDING_MS = 700

// Hindi text with small English underneath.
export function T({ hi, en }) {
  return (
    <>
      <span className="hi">{hi}</span>
      <span className="en" lang="en">{en}</span>
    </>
  )
}

export function Alert({ error }) {
  if (!error) return null
  return (
    <p className="alert" role="alert">
      <T hi={error.hi || 'कुछ गड़बड़ हुई। फिर से कोशिश करें।'} en={`Something went wrong: ${error.message}`} />
    </p>
  )
}

// Tap to start, tap to stop, auto-stop after MAX_SECONDS. onDone gets the recorded blob.
export function useRecorder(onDone) {
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState(null)
  const recorder = useRef(null)
  const startedAt = useRef(0)
  const starting = useRef(false)
  const done = useRef(onDone)
  done.current = onDone

  // Leaving the screen mid-recording discards the recording instead of uploading it.
  useEffect(() => () => {
    done.current = null
    stop()
  }, [])

  function stop() {
    if (recorder.current?.state === 'recording') recorder.current.stop()
  }

  async function start() {
    starting.current = true
    setError(null)
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      const error = new Error(`microphone unavailable (${e.name})`)
      error.hi = 'माइक्रोफ़ोन चालू नहीं हुआ। अनुमति दें और फिर दबाएँ।'
      setError(error)
      return
    } finally {
      starting.current = false
    }

    const rec = new MediaRecorder(stream)
    const chunks = []
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt.current) / 1000)
      setSeconds(elapsed)
      if (elapsed >= MAX_SECONDS) stop()
    }, 200)
    rec.ondataavailable = (e) => chunks.push(e.data)
    rec.onstop = () => {
      clearInterval(timer)
      stream.getTracks().forEach((track) => track.stop())
      setRecording(false)
      done.current?.(new Blob(chunks, { type: rec.mimeType }))
    }
    recorder.current = rec
    startedAt.current = Date.now()
    rec.start()
    setSeconds(0)
    setRecording(true)
  }

  function toggle() {
    if (starting.current) return
    if (recorder.current?.state !== 'recording') start()
    else if (Date.now() - startedAt.current >= MIN_RECORDING_MS) stop()
  }

  return { recording, seconds, error, toggle }
}

export function RecordButton({ recorder, onClick = recorder.toggle, disabled, className = '' }) {
  return (
    <button
      type="button"
      className={`record ${recorder.recording ? 'recording' : ''} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {recorder.recording ? (
        <>
          <span className="dot" aria-hidden="true" />
          <T hi="रोकने के लिए दबाएँ" en="Tap to stop" />
          <span className="seconds">
            {recorder.seconds} / {MAX_SECONDS} सेकंड
          </span>
        </>
      ) : (
        <T hi="बोलने के लिए दबाएँ" en="Tap to speak" />
      )}
    </button>
  )
}
