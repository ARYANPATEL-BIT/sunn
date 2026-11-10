import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import * as api from '../api.js'
import { useAuth } from '../auth.jsx'
import { useLang } from '../i18n/index.jsx'
import { Alert, Icon, PrimaryButton } from '../ui/index.js'
import { HonestNote } from './HonestNote.jsx'
import { SpeakWithMeStep } from './steps/SpeakWithMeStep.jsx'
import { TrainingsNav } from './TrainingsNav.jsx'

const SOUND_LABELS = {
  p: { en: 'p', hi: 'प' },
  b: { en: 'b', hi: 'ब' },
  't-dental': { en: 'soft t', hi: 'त' },
  't-retroflex': { en: 'hard t', hi: 'ट' },
  d: { en: 'd', hi: 'द' },
  k: { en: 'k', hi: 'क' },
  g: { en: 'g', hi: 'ग' },
  ch: { en: 'ch', hi: 'च' },
  j: { en: 'j', hi: 'ज' },
  s: { en: 's', hi: 'स' },
  sh: { en: 'sh', hi: 'श' },
  r: { en: 'r', hi: 'र' },
  l: { en: 'l', hi: 'ल' },
  aspirated: { en: 'breathy', hi: 'हवा वाली' },
  nasal: { en: 'nasal', hi: 'नाक वाली' },
  clusters: { en: 'clusters', hi: 'जुड़े अक्षर' },
  'th-english': { en: 'th', hi: 'th' },
}

const URGENT_KEYWORDS = [
  'urgent', 'pain', 'help', 'doctor', 'medicine', 'emergency', 'water',
  'दर्द', 'मदद', 'दवाई', 'डॉक्टर', 'पानी', 'सांस', 'तकलीफ़',
]

function isUrgent(text = '', meaning = '') {
  const combined = `${text} ${meaning}`.toLowerCase()
  return URGENT_KEYWORDS.some((kw) => combined.includes(kw.toLowerCase()))
}

export function EasierWays() {
  const { user } = useAuth()
  const { t, lang: uiLang } = useLang()
  const navigate = useNavigate()
  const location = useLocation()

  const initialText = location.state?.text || ''
  const initialLang = location.state?.lang || user?.language || 'hi'
  const initialUrgent = Boolean(location.state?.urgent)

  const [inputText, setInputText] = useState(initialText)
  const [inputLang, setInputLang] = useState(initialLang)
  const [userPhrases, setUserPhrases] = useState([])
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [playingText, setPlayingText] = useState(null)
  const [addedPhrases, setAddedPhrases] = useState(new Set())
  const [addingText, setAddingText] = useState(null)
  const [practiceAlt, setPracticeAlt] = useState(null)
  const isMounted = useRef(true)

  // Load user's phrases if logged in
  useEffect(() => {
    isMounted.current = true
    if (user) {
      api.listPhrases()
        .then((data) => {
          if (isMounted.current && Array.isArray(data)) {
            setUserPhrases(data)
          }
        })
        .catch(() => {})
    }
    return () => {
      isMounted.current = false
      api.stopAudio()
    }
  }, [user])

  // If navigated with initial text, auto-search
  useEffect(() => {
    if (initialText) {
      handleSearch(initialText, initialLang)
    }
  }, [initialText, initialLang])

  const handleLanguageChange = (newLang) => {
    if (newLang === inputLang) return
    setInputLang(newLang)
    api.stopAudio()
    setPlayingText(null)
    setPracticeAlt(null)
    if (inputText.trim()) {
      handleSearch(inputText, newLang)
    } else {
      setResults(null)
    }
  }

  const handleSearch = async (textToSearch = inputText, langToSearch = inputLang) => {
    const trimmed = (textToSearch || '').trim()
    if (!trimmed) return

    setLoading(true)
    setError(null)
    setPracticeAlt(null)
    try {
      const data = await api.getAlternatives(trimmed, langToSearch)
      if (isMounted.current) {
        setResults(data)
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err)
      }
    } finally {
      if (isMounted.current) {
        setLoading(false)
      }
    }
  }

  const handlePlayAudio = async (text) => {
    if (playingText === text) {
      api.stopAudio()
      setPlayingText(null)
      return
    }
    setPlayingText(text)
    try {
      await api.say(text, { fallback: true, language: inputLang })
    } catch {
      // Non-blocking
    } finally {
      if (isMounted.current) setPlayingText(null)
    }
  }

  const handleAddToPhrases = async (alt) => {
    if (!user) {
      navigate('/login')
      return
    }
    setAddingText(alt.text)
    try {
      let created = await api.createPhrase(alt.text)
      const shouldMarkUrgent = initialUrgent || isUrgent(alt.text, alt.meaning_en)
      if (shouldMarkUrgent) {
        created = await api.updatePhrase(created.id, { urgent: true })
      }
      setAddedPhrases((prev) => new Set([...prev, alt.text]))
    } catch (err) {
      setError(err)
    } finally {
      if (isMounted.current) setAddingText(null)
    }
  }

  const formatAvoids = (avoidsList) => {
    if (!avoidsList || avoidsList.length === 0) return ''
    return avoidsList
      .map((id) => {
        const item = SOUND_LABELS[id]
        return item ? item[uiLang] || item.en : id
      })
      .join(', ')
  }

  return (
    <div className={`trainings-page ${user ? 'with-tabs' : ''}`}>
      <TrainingsNav
        backTo="/trainings"
        backLabel={t('trainings.backToTrainings')}
      />

      <main className="trainings-content" id="easier-ways-main">
        <header className="trainings-header">
          <h1 className="display trainings-title">{t('easierWays.title')}</h1>
          <p className="lede trainings-subtitle">{t('easierWays.subtitle')}</p>
        </header>

        {/* Input & Phrase Picker Stage */}
        <section className="easier-ways-search-stage" aria-label={t('easierWays.title')}>
          <div className="easier-ways-search-card">
            {/* Language toggle */}
            <div className="easier-ways-lang-row">
              <span className="lang-row-label">{t('lang.label')}:</span>
              <div className="chips" role="radiogroup" aria-label={t('lang.label')}>
                <button
                  type="button"
                  role="radio"
                  aria-checked={inputLang === 'hi'}
                  aria-pressed={inputLang === 'hi'}
                  className={`chip lang-chip ${inputLang === 'hi' ? 'active selected' : ''}`}
                  onClick={() => handleLanguageChange('hi')}
                >
                  {inputLang === 'hi' && <Icon name="check" />}
                  <span>{t('easierWays.langHi')}</span>
                </button>
                <button
                  type="button"
                  role="radio"
                  aria-checked={inputLang === 'en'}
                  aria-pressed={inputLang === 'en'}
                  className={`chip lang-chip ${inputLang === 'en' ? 'active selected' : ''}`}
                  onClick={() => handleLanguageChange('en')}
                >
                  {inputLang === 'en' && <Icon name="check" />}
                  <span>{t('easierWays.langEn')}</span>
                </button>
              </div>
            </div>

            {/* Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSearch()
              }}
              className="easier-ways-form"
            >
              <label htmlFor="easier-ways-input" className="visually-hidden">
                {t('easierWays.inputLabel')}
              </label>
              <div className="search-input-wrap">
                <input
                  id="easier-ways-input"
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder={t('easierWays.inputPlaceholder')}
                  className="easier-ways-input"
                  lang={inputLang}
                />
                <PrimaryButton
                  type="submit"
                  disabled={loading || !inputText.trim()}
                  className="easier-ways-search-btn"
                >
                  <Icon name="search" />
                  <span>{loading ? t('easierWays.searching') : t('easierWays.searchAction')}</span>
                </PrimaryButton>
              </div>
            </form>

            {/* Quick picker from user phrases */}
            {userPhrases.length > 0 && (
              <div className="phrase-picker-strip">
                <span className="phrase-picker-label">
                  {t('easierWays.pickFromPhrases')}:
                </span>
                <div className="phrase-picker-chips">
                  {userPhrases.slice(0, 6).map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      className="chip phrase-pick-chip"
                      onClick={() => {
                        setInputText(p.text)
                        handleSearch(p.text, inputLang)
                      }}
                    >
                      {p.text}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Error Alert */}
        {error && (
          <div className="trainings-error">
            <Alert error={error} />
          </div>
        )}

        {/* Example shown when empty */}
        {!results && !loading && (
          <section className="easier-ways-example-box" aria-label={t('easierWays.exampleTitle')}>
            <span className="example-kicker">{t('easierWays.exampleTitle')}</span>
            <div className="example-content">
              <span className="example-original">{t('easierWays.exampleOriginal')}</span>
              <span className="example-arrow" aria-hidden="true">→</span>
              <div className="example-alts">
                <span className="example-pill">{t('easierWays.exampleAlt1')}</span>
                <span className="example-pill">{t('easierWays.exampleAlt2')}</span>
              </div>
            </div>
          </section>
        )}

        {/* In-Place One-Step Practice Modal / Stage */}
        {practiceAlt && (
          <section className="easier-ways-practice-modal" aria-label={t('easierWays.practiseAction')}>
            <div className="practice-modal-inner">
              <div className="practice-modal-top">
                <span className="practice-kicker">{t('easierWays.practiseAction')}</span>
                <button
                  type="button"
                  className="button small"
                  onClick={() => setPracticeAlt(null)}
                >
                  {t('easierWays.closePractice')}
                </button>
              </div>
              <SpeakWithMeStep
                step={{
                  id: `alt-${practiceAlt.text}`,
                  type: 'speak_with_me',
                  title: { en: practiceAlt.text, hi: practiceAlt.text },
                  text: practiceAlt.text,
                  latin: practiceAlt.latin,
                  meaning_en: practiceAlt.meaning_en,
                  mode: 'paced',
                  pace_wpm: [40, 100],
                  feedback: 'words',
                  language: inputLang,
                }}
                language={inputLang}
                isKids={false}
                isSmoothOrKids={false}
              />
            </div>
          </section>
        )}

        {/* Results: up to 4 alternatives as large cards */}
        {results && (
          <section className="easier-ways-results-stage" aria-label={t('easierWays.title')}>
            {results.alternatives?.length === 0 ? (
              <p className="empty-note">{t('easierWays.noResults')}</p>
            ) : (
              <div className="alternatives-grid">
                {results.alternatives.slice(0, 4).map((alt, idx) => {
                  const isAdded = addedPhrases.has(alt.text)
                  const isPlaying = playingText === alt.text
                  const isAltUrgent = initialUrgent || isUrgent(alt.text, alt.meaning_en)

                  return (
                    <article key={idx} className="alternative-card">
                      <div className="alt-card-header">
                        {isAltUrgent && (
                          <span className="alt-urgent-note">
                            <span className="mark-urgent" aria-hidden="true" />
                            {t('easierWays.urgentNote')}
                          </span>
                        )}
                        <span className="alt-source-pill">
                          {t(alt.source === 'library' ? 'easierWays.sourceLibrary' : 'easierWays.sourceAssistant')}
                        </span>
                      </div>

                      <div className="alt-card-body">
                        <p className="alt-phrase-text" lang={inputLang}>
                          {alt.text}
                        </p>
                        {alt.latin && <p className="alt-latin-text">{alt.latin}</p>}
                        {alt.meaning_en && (
                          <p className="alt-meaning-text">{alt.meaning_en}</p>
                        )}
                        {alt.avoids?.length > 0 && (
                          <p className="alt-avoids-line">
                            {t('easierWays.avoids', {
                              sounds: formatAvoids(alt.avoids),
                            })}
                          </p>
                        )}
                      </div>

                      <div className="alt-card-actions">
                        {/* 1. Listen */}
                        <button
                          type="button"
                          className="button alt-action-btn"
                          onClick={() => handlePlayAudio(alt.text)}
                          aria-label={`${t('easierWays.listenAction')}: ${alt.text}`}
                        >
                          <Icon name={isPlaying ? 'stop' : 'volume'} />
                          <span>{t(isPlaying ? 'step.playing' : 'easierWays.listenAction')}</span>
                        </button>

                        {/* 2. Practise */}
                        <button
                          type="button"
                          className="button alt-action-btn"
                          onClick={() => setPracticeAlt(alt)}
                        >
                          <Icon name="play" />
                          <span>{t('easierWays.practiseAction')}</span>
                        </button>

                        {/* 3. Add to my phrases */}
                        <button
                          type="button"
                          className={`button alt-action-btn ${isAdded ? 'added' : ''}`}
                          onClick={() => handleAddToPhrases(alt)}
                          disabled={addingText === alt.text || isAdded}
                        >
                          <Icon name={isAdded ? 'check' : 'plus'} />
                          <span>
                            {isAdded ? t('phrases.enrolledStatus', { enrolled: 1, needed: 1 }) : t('easierWays.addPhraseAction')}
                          </span>
                        </button>
                      </div>

                      {isAdded && (
                        <div className="alt-added-notice">
                          <p className="added-msg">{t('easierWays.addedSuccess')}</p>
                          <button
                            type="button"
                            className="button small"
                            onClick={() => navigate('/app/enroll')}
                          >
                            {t('easierWays.teachPhraseAction')}
                          </button>
                        </div>
                      )}
                    </article>
                  )
                })}
              </div>
            )}
          </section>
        )}

        <HonestNote />
      </main>
    </div>
  )
}
