import { useEffect, useRef, useState } from 'react'
import { useLang } from './i18n/index.jsx'
import {
  Band, CONTEXT_BAND, Grille, Icon, Label, PushButton, Readout, ReadoutRow, reducedMotion,
} from './ui/index.js'

// Made-up examples, labelled as such on the device: what a speech service might hear from
// unclear speech, and the phrase Sunn says. Never real recordings. The phone further down the
// page shows the ranked alternates.
const EXAMPLES = [
  { raw: 'baani chaiye…', phrase: 'पानी चाहिए' },
  { raw: 'dad ho ra hai…', phrase: 'दर्द हो रहा है' },
  { raw: 'bede go bulao…', phrase: 'बेटे को बुलाओ' },
]
// How long each phase lasts (ms): someone speaking (the blob wobbles), Sunn matching what the
// speech service heard, then the phrase resolved and staying a moment.
const PHASES = [
  ['wave', 2000],
  ['heard', 1300],
  ['said', 3800],
]
const BLOB = { wave: 'listening', heard: 'thinking', said: 'rest' }
const RECORD = { wave: 'recording', heard: 'waiting', said: 'idle' }
const STATUS = { wave: 'device.status_listening', heard: 'device.status_thinking', said: 'device.status_result' }

// No microphone on the landing page: a made-up loudness curve with syllable-like bursts.
function fakeLevel() {
  const s = performance.now() / 1000
  const syllables = Math.max(0, Math.sin(s * 9.1)) * (0.55 + 0.45 * Math.sin(s * 2.3 + 1))
  return Math.min(1, 0.18 + 0.7 * syllables)
}

// The device on the landing page, built from the app's own parts, cycling three examples.
export default function Example() {
  const { t } = useLang()
  const still = reducedMotion()
  const [index, setIndex] = useState(0)
  const [phase, setPhase] = useState(still ? 2 : 0)
  const [playing, setPlaying] = useState(!still)
  const level = useRef({
    get current() {
      return fakeLevel()
    },
  }).current

  useEffect(() => {
    if (!playing) return
    const timer = setTimeout(() => {
      if (phase < PHASES.length - 1) return setPhase(phase + 1)
      setPhase(0)
      setIndex((index + 1) % EXAMPLES.length)
    }, PHASES[phase][1])
    return () => clearTimeout(timer)
  }, [playing, phase, index])

  // Paused mid-way: show the finished example, not a half-resolved one.
  function toggle() {
    if (playing) setPhase(PHASES.length - 1)
    setPlaying(!playing)
  }

  const example = EXAMPLES[index]
  const gloss = t('example.gloss')[index]
  const name = PHASES[phase][0]

  return (
    <figure className="device device-object example" data-phase={name}>
      <div className="example-head">
        <Grille className="grille-strip" />
        <div className="example-bar">
          <Label k="example.label" inline as="figcaption" className="example-label" />
          <button
            type="button"
            className="icon-button"
            onClick={toggle}
            aria-label={t(playing ? 'example.pause' : 'example.play')}
          >
            <Icon name={playing ? 'pause' : 'play'} />
          </button>
        </div>
      </div>

      {/* The animation is for eyes; screen readers get the three examples as plain sentences. */}
      <ul className="visually-hidden">
        {EXAMPLES.map((e) => (
          <li key={e.raw}>{t('example.describe', { raw: e.raw.replace('…', ''), phrase: e.phrase })}</li>
        ))}
      </ul>

      <div className="example-face" aria-hidden="true">
        <Readout blobState={BLOB[name]} level={level} top={<Label k={STATUS[name]} inline className="readout-status" />}>
          <ReadoutRow label="device.heard" className={name === 'wave' ? 'is-empty' : ''}>
            <p className="readout-heard" key={`heard-${index}`}>
              <span lang="hi-Latn">“{example.raw}”</span>
            </p>
          </ReadoutRow>
          <ReadoutRow label="device.understood" className={name === 'said' ? '' : 'is-empty'}>
            <div className="candidate top" key={`said-${index}-${name}`}>
              <span className="candidate-text" lang="hi">
                {example.phrase}
              </span>
              {gloss && (
                <span className="gloss" lang="en">
                  {gloss}
                </span>
              )}
            </div>
          </ReadoutRow>
        </Readout>
        <Band still title="device.place" options={CONTEXT_BAND} value="any" />
        <PushButton static state={RECORD[name]} label={name === 'said' ? t('sun.again') : undefined} />
      </div>
    </figure>
  )
}
