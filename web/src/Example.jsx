import { Pause, Play, Volume2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useLang } from './i18n/index.jsx'
import { RecordCircle } from './record.jsx'
import { ICON, reducedMotion } from './ui.jsx'

// Made-up examples, labelled as such on screen: what a speech service might hear from unclear
// speech, the phrase Sunn says, and the two next closest. Never real recordings.
const EXAMPLES = [
  { raw: 'baani chaiye…', phrase: 'पानी चाहिए', alternates: ['मदद चाहिए', 'दवाई दे दो'] },
  { raw: 'dad ho ra hai…', phrase: 'दर्द हो रहा है', alternates: ['ठंड लग रही है', 'भूख लगी है'] },
  { raw: 'bede go bulao…', phrase: 'बेटे को बुलाओ', alternates: ['डॉक्टर को बुलाओ', 'मुझे उठा दो'] },
]
// How long each phase lasts (ms): recording, then what the speech service heard while Sunn
// matches it, then the phrase resolved and staying a moment.
const PHASES = [
  ['wave', 1400],
  ['heard', 1500],
  ['said', 3600],
]
const CONTEXTS = ['any', 'home', 'hospital', 'market']

// The Speak screen, resolving one example after another: the app's own record button,
// candidate card and alternate rows, with nothing to press.
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

  // Paused mid-way: show the finished example, not a half-resolved one.
  function toggle() {
    if (playing) setPhase(PHASES.length - 1)
    setPlaying(!playing)
  }

  const example = EXAMPLES[index]
  const gloss = t('example.gloss')[index]
  const name = PHASES[phase][0]
  const record = { wave: ['recording', 'sun.stop'], heard: ['waiting', 'sun.listening'], said: ['idle', 'sun.again'] }[name]

  return (
    <figure className="stage example" data-phase={name}>
      <div className="stage-top">
        <figcaption className="stage-label">{t('example.label')}</figcaption>
        <button
          type="button"
          className="icon-button"
          onClick={toggle}
          aria-label={t(playing ? 'example.pause' : 'example.play')}
        >
          {playing ? <Pause {...ICON} /> : <Play {...ICON} />}
        </button>
      </div>

      {/* The animation is for eyes; screen readers get the three examples as plain sentences. */}
      <ul className="visually-hidden">
        {EXAMPLES.map((e) => (
          <li key={e.raw}>{t('example.describe', { raw: e.raw.replace('…', ''), phrase: e.phrase })}</li>
        ))}
      </ul>

      <div className="example-screen" aria-hidden="true" key={index}>
        <div className="chips">
          {CONTEXTS.map((context) => (
            <span key={context} className={`chip ${context === 'any' ? 'on' : ''}`}>
              {t(`speak.context_${context}`)}
            </span>
          ))}
        </div>
        <p className="heard">
          {t('speak.heard')} <span lang="hi-Latn">“{example.raw}”</span>
        </p>
        <div className="candidate top">
          <span className="candidate-text" lang="hi">
            {example.phrase}
          </span>
          {gloss && (
            <span className="gloss" lang="en">
              {gloss}
            </span>
          )}
        </div>
        <div className="group alternates">
          {example.alternates.map((text) => (
            <div key={text} className="row candidate">
              <span className="row-title" lang="hi">
                {text}
              </span>
              <Volume2 className="row-icon" {...ICON} />
            </div>
          ))}
        </div>
        <div className="record-wrap compact">
          <div className={`record ${record[0]}`}>
            <RecordCircle state={record[0]} />
            <span className="record-label">{t(record[1])}</span>
          </div>
        </div>
      </div>
    </figure>
  )
}
