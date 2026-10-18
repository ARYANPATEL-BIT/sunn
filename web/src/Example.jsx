import { Pause, Play } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLang } from './i18n/index.jsx'
import { reducedMotion } from './ui.jsx'

// Made-up examples, labelled as such on screen: what a speech service might hear from unclear
// speech, and the phrase Sunn says. Never real recordings.
const EXAMPLES = [
  { raw: 'baani chaiye…', phrase: 'पानी चाहिए' },
  { raw: 'dad ho ra hai…', phrase: 'दर्द हो रहा है' },
  { raw: 'bede go bulao…', phrase: 'बेटे को बुलाओ' },
]
// How long each phase lasts (ms): the waveform alone, then the blurred transcript, then the
// phrase resolving and staying a moment.
const PHASES = [
  ['wave', 1400],
  ['heard', 1500],
  ['said', 3600],
]
// A fixed waveform shape (bar heights 0..1), so it's the same on every render.
const BARS = Array.from({ length: 36 }, (_, i) => 0.18 + 0.82 * Math.abs(Math.sin(i * 0.9) * Math.sin(i * 0.31 + 1)))

export default function Example() {
  const { t } = useLang()
  const still = reducedMotion()
  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState(still ? 2 : 0)
  const [playing, setPlaying] = useState(!still)

  useEffect(() => {
    if (!playing) return
    const timer = setTimeout(() => {
      if (phase < PHASES.length - 1) return setPhase(phase + 1)
      setPhase(0)
      setIndex((index + 1) % EXAMPLES.length)
    }, PHASES[phase][1])
    return () => clearTimeout(timer)
  }, [playing, phase, index])

  // Paused mid-way: show the finished example, not a half-blurred one.
  function toggle() {
    if (playing) setPhase(PHASES.length - 1)
    setPlaying(!playing)
  }

  const example = EXAMPLES[index]
  const gloss = t('example.gloss')[index]
  const name = PHASES[phase][0]

  return (
    <figure className="example" data-phase={name}>
      <div className="example-top">
        <figcaption className="example-label">{t('example.label')}</figcaption>
        <button
          type="button"
          className="icon-button"
          onClick={toggle}
          aria-label={t(playing ? 'example.pause' : 'example.play')}
        >
          {playing ? <Pause aria-hidden="true" strokeWidth={1.5} /> : <Play aria-hidden="true" strokeWidth={1.5} />}
        </button>
      </div>

      {/* The animation is for eyes; screen readers get the three examples as plain sentences. */}
      <ul className="visually-hidden">
        {EXAMPLES.map((e) => (
          <li key={e.raw}>{t('example.describe', { raw: e.raw.replace('…', ''), phrase: e.phrase })}</li>
        ))}
      </ul>

      <div className="example-stage" aria-hidden="true" key={index}>
        <svg className="wave" viewBox={`0 0 ${BARS.length * 8} 48`} preserveAspectRatio="none">
          {BARS.map((h, i) => (
            <rect key={i} x={i * 8 + 2} y={24 - h * 22} width="3" height={h * 44} rx="1.5" style={{ '--i': i }} />
          ))}
        </svg>
        <div className="example-row">
          <span className="example-row-label">{t('example.heard')}</span>
          <span className="raw" lang="hi-Latn">
            {example.raw}
          </span>
        </div>
        <div className="example-row">
          <span className="example-row-label">{t('example.understood')}</span>
          <span className="resolved" lang="hi">
            {example.phrase}
          </span>
          {gloss && (
            <span className="gloss" lang="en">
              {gloss}
            </span>
          )}
        </div>
      </div>
    </figure>
  )
}
