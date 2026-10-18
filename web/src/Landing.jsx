import {
  ArrowDown,
  ArrowRight,
  AudioLines,
  Building2,
  Ear,
  Fingerprint,
  HeartHandshake,
  Info,
  Languages,
  MessageCircle,
  Mic,
  Plus,
  ShieldCheck,
  Trash2,
  Volume2,
  Waves,
} from 'lucide-react'
import { Fragment, useId, useState } from 'react'
import { Link } from 'react-router-dom'
import * as api from './api.js'
import { loginPath, useAuth } from './auth.jsx'
import Example from './Example.jsx'
import { useLang } from './i18n/index.jsx'
import { LangToggle, Pill, reducedMotion, useGo, Wordmark } from './ui.jsx'

const ICON = { 'aria-hidden': true, strokeWidth: 1.25 }

// Signed in: speak, or teach first if nothing is enrolled yet. Signed out: log in, then speak.
function useStartSpeaking() {
  const { status, user } = useAuth()
  const go = useGo()
  return async () => {
    if (status === 'ready' && !user) return go(loginPath('/app/speak'))
    const phrases = await api.listPhrases().catch(() => null)
    go(phrases && !phrases.some((p) => p.enrolled > 0) ? '/app/enroll' : '/app/speak')
  }
}

function SiteNav() {
  const { t } = useLang()
  const { user } = useAuth()
  return (
    <header className="site-nav">
      <Wordmark />
      <nav className="site-nav-end" aria-label={t('nav.main')}>
        <ul className="site-links">
          <li>
            <a href="#how">{t('nav.how')}</a>
          </li>
          <li>
            <a href="#who">{t('nav.who')}</a>
          </li>
          <li>
            <a href="#privacy">{t('nav.privacy')}</a>
          </li>
        </ul>
        <LangToggle />
        <Link className="pill-outline" to={user ? '/app/speak' : '/login'} viewTransition={!reducedMotion()}>
          {t(user ? 'nav.openApp' : 'nav.signIn')}
        </Link>
      </nav>
    </header>
  )
}

function Hero({ onStart }) {
  const { t } = useLang()
  const features = [
    [AudioLines, 'feature.learns'],
    [Volume2, 'feature.speaks'],
    [Languages, 'feature.languages'],
  ]
  return (
    <section className="hero">
      <div className="hero-center">
        <h1 className="hero-title">
          <span className="hero-mark" lang="en">
            Sunn
          </span>
          <span className="hero-headline">{t('hero.headline')}</span>
        </h1>
        <p className="hero-lines">
          <span>{t('hero.line1')}</span>
          <span>{t('hero.line2')}</span>
        </p>
        <Pill className="pill-glow" onClick={onStart}>
          {t('cta.start')}
        </Pill>
      </div>
      <ul className="features">
        {features.map(([Icon, key]) => (
          <li key={key}>
            <Icon {...ICON} />
            <span>{t(key)}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function SectionHead({ id, title, children }) {
  return (
    <div className="section-head">
      <h2 id={id}>{title}</h2>
      {children}
    </div>
  )
}

function How() {
  const { t } = useLang()
  return (
    <section className="section how" id="how" aria-labelledby="how-title">
      <SectionHead id="how-title" title={t('how.title')} />
      <div className="how-grid">
        <ol className="steps">
          {t('how.steps').map((step, i) => (
            <li key={i}>
              <span className="step-number" aria-hidden="true">
                {String(i + 1).padStart(2, '0')}
              </span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
            </li>
          ))}
        </ol>
        <Example />
      </div>
    </section>
  )
}

function OwnVoice() {
  const { t } = useLang()
  return (
    <section className="section voice" aria-labelledby="voice-title">
      <p className="tag">
        <span>{t('voice.status')}</span>
        <span className="visually-hidden">. {t('voice.statusNote')}</span>
      </p>
      <h2 id="voice-title" className="display">
        {t('voice.title')}
      </h2>
      <p className="lede">{t('voice.body')}</p>
    </section>
  )
}

function Who() {
  const { t } = useLang()
  const icons = [MessageCircle, HeartHandshake, Building2]
  return (
    <section className="section" id="who" aria-labelledby="who-title">
      <SectionHead id="who-title" title={t('who.title')} />
      <ul className="columns">
        {t('who.items').map((item, i) => {
          const Icon = icons[i]
          return (
            <li key={i}>
              <Icon {...ICON} />
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function UnderTheHood() {
  const { t } = useLang()
  const icons = [Mic, Waves, Fingerprint, Volume2]
  return (
    <section className="section" aria-labelledby="hood-title">
      <SectionHead id="hood-title" title={t('hood.title')} />
      <ol className="pipeline">
        {t('hood.steps').map((step, i) => {
          const Icon = icons[i]
          return (
            <Fragment key={i}>
              {i > 0 && (
                <li className="pipeline-arrow" aria-hidden="true">
                  <ArrowRight {...ICON} className="across" />
                  <ArrowDown {...ICON} className="down" />
                </li>
              )}
              <li className="pipeline-step">
                <Icon {...ICON} />
                <h3 lang={step.title.startsWith('Gnani') ? 'en' : undefined}>{step.title}</h3>
                <p>{step.body}</p>
              </li>
            </Fragment>
          )
        })}
      </ol>
    </section>
  )
}

function Privacy() {
  const { t } = useLang()
  const icons = [ShieldCheck, Ear, Trash2, Info]
  return (
    <section className="section" id="privacy" aria-labelledby="privacy-title">
      <SectionHead id="privacy-title" title={t('privacy.title')} />
      <ul className="columns four">
        {t('privacy.items').map((item, i) => {
          const Icon = icons[i]
          return (
            <li key={i}>
              <Icon {...ICON} />
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function Faq() {
  const { t } = useLang()
  const base = useId()
  const [open, setOpen] = useState(null)
  return (
    <section className="section faq" aria-labelledby="faq-title">
      <SectionHead id="faq-title" title={t('faq.title')} />
      <div className="faq-list">
        {t('faq.items').map((item, i) => {
          const expanded = open === i
          return (
            <div className="faq-item" key={i}>
              <h3>
                <button
                  type="button"
                  id={`${base}-q${i}`}
                  aria-expanded={expanded}
                  aria-controls={`${base}-a${i}`}
                  onClick={() => setOpen(expanded ? null : i)}
                >
                  <span>{item.q}</span>
                  <Plus {...ICON} className="faq-icon" />
                </button>
              </h3>
              <div id={`${base}-a${i}`} role="region" aria-labelledby={`${base}-q${i}`} hidden={!expanded}>
                <p>{item.a}</p>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function Closing({ onStart }) {
  const { t } = useLang()
  return (
    <section className="section closing" aria-labelledby="closing-title">
      <h2 id="closing-title" className="display">
        {t('closing.line')}
      </h2>
      <Pill className="pill-glow" onClick={onStart}>
        {t('cta.start')}
      </Pill>
    </section>
  )
}

function Footer() {
  const { t } = useLang()
  return (
    <footer className="site-footer">
      <Wordmark />
      <p>{t('footer.built')}</p>
      <p>{t('footer.made')}</p>
    </footer>
  )
}

export default function Landing() {
  const start = useStartSpeaking()
  return (
    <div className="landing">
      <SiteNav />
      <main>
        <Hero onStart={start} />
        <How />
        <OwnVoice />
        <Who />
        <UnderTheHood />
        <Privacy />
        <Faq />
        <Closing onStart={start} />
      </main>
      <Footer />
    </div>
  )
}
