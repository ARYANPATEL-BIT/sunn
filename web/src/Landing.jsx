import { Link } from 'react-router-dom'
import * as api from './api.js'
import { loginPath, useAuth } from './auth.jsx'
import Example from './Example.jsx'
import { useLang } from './i18n/index.jsx'
import { speakProgress } from './quickstart.js'
import {
  Band, CONTEXT_BAND, Grille, Icon, LangToggle, Label, PrimaryButton, PushButton, RankedFace, RankedList, Readout,
  ReadoutRow, reducedMotion, ThemeToggle, useGo, Wordmark,
} from './ui/index.js'
import { TabFace, TABS } from './ui/Tabs.jsx'

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
        <ul className="nav-links">
          <li>
            <a href="#how">{t('how.title')}</a>
          </li>
          <li>
            <a href="#privacy">{t('privacy.title')}</a>
          </li>
          <li>
            <a href="#faq">{t('nav.faq')}</a>
          </li>
        </ul>
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
  const { t, bi, lang } = useLang()
  const other = lang === 'hi' ? 'en' : 'hi'
  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero-copy">
        <h1 className="display" id="hero-title">
          {t('hero.headline')}
        </h1>
        <p className="display-other" lang={other}>
          {bi('hero.headline')[other]}
        </p>
        <p className="lede">{t('hero.line2')}</p>
        <div className="hero-actions">
          <PrimaryButton icon="mic" onClick={onStart}>
            {t('cta.start')}
          </PrimaryButton>
          <a className="text-link" href="#how">
            {t('hero.link')}
          </a>
        </div>
      </div>
      <div className="hero-device">
        <Example />
      </div>
    </section>
  )
}

// A spec sheet line: four facts, divided by hairlines, no boxes.
function Specs() {
  const { t } = useLang()
  return (
    <section className="specs" aria-labelledby="spec-title">
      <h2 className="visually-hidden" id="spec-title">
        {t('spec.title')}
      </h2>
      <dl className="spec-strip">
        {t('spec.items').map((item) => (
          <div className="spec" key={item.label}>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

// Made-up, in the language the account would speak: the Speak screen as it looks after a phrase.
const PHONE = {
  hi: { raw: 'baani chaiye', phrase: 'पानी चाहिए', alternates: ['मदद चाहिए', 'दवाई दे दो'] },
  en: { raw: 'ai nee waw', phrase: 'I need water', alternates: ['I need help', 'Give me my medicine'] },
}

// The phone: the app's own Speak screen, still, in a phone frame. A picture, so aria-hidden.
function Phone() {
  const { lang } = useLang()
  const example = PHONE[lang]
  return (
    <div className="phone" aria-hidden="true">
      <div className="phone-screen">
        <div className="phone-bar">
          <span className="wordmark">
            <span className="wordmark-latin">Sunn</span>
            <span className="wordmark-hi" lang="hi">
              सुन
            </span>
          </span>
        </div>
        <div className="device speak-device phone-device">
          <Grille className="grille-strip" />
          <Readout blobState="rest" top={<Label k="device.status_result" inline className="readout-status" />}>
            <ReadoutRow label="device.heard">
              <p className="readout-heard">
                <span lang={lang === 'hi' ? 'hi-Latn' : 'en'}>“{example.raw}”</span>
              </p>
            </ReadoutRow>
            <ReadoutRow label="device.understood">
              <div className="candidate top">
                <span className="candidate-text" lang={lang}>
                  {example.phrase}
                </span>
              </div>
            </ReadoutRow>
          </Readout>
          <RankedList>
            {example.alternates.map((text, i) => (
              <div key={text} className="ranked-row">
                <RankedFace n={i + 2} icon="volume">
                  <span className="candidate-text" lang={lang}>
                    {text}
                  </span>
                </RankedFace>
              </div>
            ))}
          </RankedList>
          <Band still options={CONTEXT_BAND} value="home" />
          <PushButton static state="idle" />
        </div>
        <div className="tabs phone-tabs">
          <div className="tabs-inner">
            {TABS.map(({ to, key, icon }) => (
              <span key={to} className={`tab ${to === '/app/speak' ? 'active' : ''}`}>
                <TabFace k={key} icon={icon} />
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function Pocket() {
  const { t } = useLang()
  return (
    <section className="section pocket" id="how" aria-labelledby="pocket-title">
      <div className="pocket-copy">
        <h2 className="section-title" id="pocket-title">
          {t('pocket.title')}
        </h2>
        <p className="lede">{t('pocket.body')}</p>
        <ol className="steps">
          {t('pocket.steps').map((step, i) => (
            <li key={step}>
              <span className="step-n" aria-hidden="true">
                {i + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </div>
      <div className="pocket-phone">
        <Phone />
      </div>
    </section>
  )
}

function OwnVoice() {
  const { t, lang } = useLang()
  return (
    <section className="section text-section" aria-labelledby="voice-title">
      <h2 className="section-title" id="voice-title">
        {t('voice.title')}
      </h2>
      <div className="text-section-body">
        <p className="lede">{t('voice.body')}</p>
        <p className="small-print">
          {t('voice.status')}
          {lang === 'hi' ? '। ' : '. '}
          {t('voice.statusNote')}
        </p>
      </div>
    </section>
  )
}

function Privacy() {
  const { t } = useLang()
  return (
    <section className="section text-section" id="privacy" aria-labelledby="privacy-title">
      <h2 className="section-title" id="privacy-title">
        {t('privacy.headline')}
      </h2>
      <ul className="rule-list">
        {t('privacy.items').map((item) => (
          <li key={item.title}>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Faq() {
  const { t } = useLang()
  return (
    <section className="section text-section" id="faq" aria-labelledby="faq-title">
      <h2 className="section-title" id="faq-title">
        {t('faq.title')}
      </h2>
      <div className="faq">
        {t('faq.items').map((item) => (
          <details key={item.q} className="faq-item">
            <summary>
              <span>{item.q}</span>
              <Icon name="plus" className="faq-icon" />
            </summary>
            <p>{item.a}</p>
          </details>
        ))}
      </div>
    </section>
  )
}

function Footer() {
  const { t } = useLang()
  return (
    <footer className="site-footer">
      <Wordmark />
      <div>
        <p>{t('footer.built')}</p>
        <p>{t('footer.made')}</p>
      </div>
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
        <Specs />
        <Pocket />
        <OwnVoice />
        <Privacy />
        <Faq />
      </main>
      <Footer />
    </div>
  )
}
