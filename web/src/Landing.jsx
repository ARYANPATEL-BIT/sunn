import { ChevronRight, Ear, Fingerprint, Info, Mic, PencilLine, ShieldCheck, Trash2, Volume2, Waves } from 'lucide-react'
import { Link } from 'react-router-dom'
import * as api from './api.js'
import { loginPath, useAuth } from './auth.jsx'
import Example from './Example.jsx'
import { useLang } from './i18n/index.jsx'
import { speakProgress } from './quickstart.js'
import { RecordCircle } from './record.jsx'
import { ICON, LangToggle, Pill, reducedMotion, ThemeToggle, useGo, Wordmark } from './ui.jsx'

// Signed in: speak, or record the first phrases if Speak isn't open yet. Signed out: log in, then speak.
function useStartSpeaking() {
  const { status, user } = useAuth()
  const go = useGo()
  return async () => {
    if (status === 'ready' && !user) return go(loginPath('/app/speak'))
    const phrases = await api.listPhrases().catch(() => null)
    go(phrases && user && !speakProgress(phrases, user.language).open ? '/app/enroll' : '/app/speak')
  }
}

function SiteNav() {
  const { t } = useLang()
  const { user } = useAuth()
  return (
    <header className="site-nav">
      <nav className="bar" aria-label={t('nav.main')}>
        <Wordmark />
        <div className="bar-end">
          <LangToggle />
          <ThemeToggle />
          <Link className="nav-link" to={user ? '/app/speak' : '/login'} viewTransition={!reducedMotion()}>
            {t(user ? 'nav.openApp' : 'nav.signIn')}
          </Link>
        </div>
      </nav>
    </header>
  )
}

function Hero({ onStart }) {
  const { t } = useLang()
  return (
    <section className="hero">
      <p className="eyebrow" lang="en">
        Sunn
      </p>
      <h1 className="display">{t('hero.headline')}</h1>
      <p className="lede">{t('hero.line2')}</p>
      <Pill icon={Mic} onClick={onStart}>
        {t('cta.start')}
      </Pill>
    </section>
  )
}

// One point per section: a small label, a big headline, one line, then something to see.
function Section({ id, eyebrow, title, lede, alt, children }) {
  return (
    <section className={`section ${alt ? 'alt' : ''}`} aria-labelledby={id}>
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h2 className="section-title" id={id}>
        {title}
      </h2>
      {lede && <p className="lede">{lede}</p>}
      <div className="visual">{children}</div>
    </section>
  )
}

// Made-up phrases, labelled as an example, in the language the page is shown in.
const FIX_EXAMPLE = {
  en: { heard: 'plee oben de window…', candidates: ['Help me sit up', 'Give me my medicine'], typed: 'Please open the window' },
  hi: { heard: 'khirki kol do…', candidates: ['मुझे उठा दो', 'दवाई दे दो'], typed: 'खिड़की खोल दो' },
}

// The correction loop as it looks in Speak: two wrong guesses, "None of these", and the sheet
// with the phrase the person meant.
function Correction() {
  const { t, lang } = useLang()
  const example = FIX_EXAMPLE[lang]
  return (
    <figure className="stage fix-stage">
      <figcaption className="stage-label">{t('example.label')}</figcaption>
      <div aria-hidden="true">
        <p className="heard">
          {t('speak.heard')} <span lang={lang === 'hi' ? 'hi-Latn' : 'en'}>“{example.heard}”</span>
        </p>
        <div className="group alternates">
          {example.candidates.map((text) => (
            <div key={text} className="row candidate">
              <span className="row-title" lang={lang}>
                {text}
              </span>
              <Volume2 className="row-icon" {...ICON} />
            </div>
          ))}
          <div className="row none-row">
            <PencilLine className="row-icon" {...ICON} />
            <span className="row-title">{t('speak.noneOfThese')}</span>
            <ChevronRight className="row-chevron" {...ICON} />
          </div>
        </div>
        <div className="stage-scrim" />
        <div className="sheet sheet-static">
          <div className="sheet-body">
            <div className="group">
              <div className="field-cell">
                <span className="field-label">{t('speak.typeLabel')}</span>
                <span className="field-value" lang={lang}>
                  {example.typed}
                  <span className="caret" />
                </span>
              </div>
            </div>
            <div className="actions">
              <span className="button">{t('speak.cancel')}</span>
              <span className="pill">{t('speak.sayIt')}</span>
            </div>
          </div>
        </div>
      </div>
      <p className="visually-hidden">{t('landing.fixBody')}</p>
    </figure>
  )
}

// The voice rows from Settings, as they look once a voice has been added.
function OwnVoice() {
  const { t } = useLang()
  return (
    <figure>
      <div className="group" aria-hidden="true">
        <div className="row">
          <span className="row-text">
            <span className="row-title">{t('settings.voiceStatusLabel')}</span>
            <span className="row-sub">{t('settings.voiceRecorded')}</span>
          </span>
        </div>
        <div className="row">
          <span className="row-title">{t('settings.useOwnVoiceLabel')}</span>
          <span className="switch on" />
        </div>
        <div className="row">
          <span className="row-title">{t('settings.testVoice')}</span>
          <Volume2 className="row-icon" {...ICON} />
        </div>
      </div>
    </figure>
  )
}

function Pipeline() {
  const { t } = useLang()
  const icons = [Mic, Waves, Fingerprint, Volume2]
  return (
    <ol className="group pipeline">
      {t('hood.steps').map((step, i) => {
        const Icon = icons[i]
        return (
          <li key={i} className="row">
            <span className="row-badge">
              <Icon {...ICON} />
            </span>
            <span className="row-text">
              <span className="row-title" lang={step.title.startsWith('Gnani') ? 'en' : undefined}>
                {step.title}
              </span>
              <span className="row-sub">{step.body}</span>
            </span>
          </li>
        )
      })}
    </ol>
  )
}

function Privacy() {
  const { t } = useLang()
  const icons = [ShieldCheck, Ear, Trash2, Info]
  return (
    <ul className="group">
      {t('privacy.items').map((item, i) => {
        const Icon = icons[i]
        return (
          <li key={i} className="row">
            <span className="row-badge">
              <Icon {...ICON} />
            </span>
            <span className="row-text">
              <span className="row-title">{item.title}</span>
              <span className="row-sub">{item.body}</span>
            </span>
          </li>
        )
      })}
    </ul>
  )
}

function Footer() {
  const { t } = useLang()
  return (
    <footer className="site-footer">
      <p className="footer-built">{t('footer.built')}</p>
      <p>{t('footer.made')}</p>
    </footer>
  )
}

export default function Landing() {
  const { t } = useLang()
  const start = useStartSpeaking()
  return (
    <div className="landing">
      <SiteNav />
      <main>
        <Hero onStart={start} />
        <Section id="speak-title" eyebrow={t('how.title')} title={t('hero.line1')} lede={t('landing.speakBody')} alt>
          <Example />
        </Section>
        <Section id="fix-title" eyebrow={t('landing.fixEyebrow')} title={t('landing.fixTitle')} lede={t('landing.fixBody')}>
          <Correction />
        </Section>
        <Section
          id="voice-title"
          eyebrow={
            <>
              {t('voice.status')}
              <span className="visually-hidden">. {t('voice.statusNote')}</span>
            </>
          }
          title={t('voice.title')}
          lede={t('voice.body')}
          alt
        >
          <OwnVoice />
        </Section>
        <Section id="hood-title" eyebrow={t('hood.title')} title={t('hood.headline')} lede={t('hood.body')}>
          <Pipeline />
        </Section>
        <Section id="privacy-title" eyebrow={t('privacy.title')} title={t('privacy.headline')} alt>
          <Privacy />
        </Section>
        <section className="section closing" aria-labelledby="closing-title">
          <RecordCircle state="idle" />
          <h2 className="section-title" id="closing-title">
            {t('closing.line')}
          </h2>
          <Pill icon={Mic} onClick={start}>
            {t('cta.start')}
          </Pill>
        </section>
      </main>
      <Footer />
    </div>
  )
}
