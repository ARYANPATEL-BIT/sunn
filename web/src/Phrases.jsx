import { Check, Pencil, Plus, RotateCcw, Search, Square, Trash2, Volume2, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { Alert, Pill, useGo } from './ui.jsx'

const CONTEXT_OPTIONS = ['any', 'home', 'hospital', 'market']
const NEEDED_RECORDINGS = 3

export default function Phrases() {
  const { t } = useLang()
  const { user } = useAuth()
  const go = useGo()

  const [phrases, setPhrases] = useState(null)
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState('all') // 'all', 'urgent', 'home', 'hospital', 'market'

  // Modals / Panels
  const [isAdding, setIsAdding] = useState(false)
  const [addText, setAddText] = useState('')
  const [addContexts, setAddContexts] = useState(['any'])
  const [addUrgent, setAddUrgent] = useState(false)

  const [editingPhrase, setEditingPhrase] = useState(null)
  const [editText, setEditText] = useState('')
  const [editContexts, setEditContexts] = useState(['any'])
  const [editUrgent, setEditUrgent] = useState(false)

  const [deletingPhrase, setDeletingPhrase] = useState(null)

  // Status & Feedback
  const [busy, setBusy] = useState(null) // 'loading', 'adding', 'updating', 'deleting', 'defaults', 'playing'
  const [playingText, setPlayingText] = useState(null)
  const [error, setError] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const isMounted = useRef(true)

  const loadPhrases = async () => {
    setBusy('loading')
    setError(null)
    try {
      const data = await api.listPhrases()
      if (isMounted.current) {
        setPhrases(data)
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err)
      }
    } finally {
      if (isMounted.current) {
        setBusy(null)
      }
    }
  }

  useEffect(() => {
    isMounted.current = true
    loadPhrases()
    return () => {
      isMounted.current = false
      api.stopAudio()
    }
  }, [])

  const flashFeedback = (msgKey) => {
    setFeedback(t(msgKey))
    setTimeout(() => {
      if (isMounted.current) setFeedback(null)
    }, 4000)
  }

  // --- Audio Playback ---
  const handlePlay = async (phraseText) => {
    if (playingText === phraseText) {
      api.stopAudio()
      setPlayingText(null)
      return
    }
    setPlayingText(phraseText)
    try {
      await api.say(phraseText)
    } catch (e) {
      setError(e)
    } finally {
      if (isMounted.current) {
        setPlayingText(null)
      }
    }
  }

  // --- Add Phrase ---
  const handleOpenAdd = () => {
    setAddText('')
    setAddContexts(['any'])
    setAddUrgent(false)
    setError(null)
    setIsAdding(true)
  }

  const handleToggleAddContext = (ctx) => {
    if (ctx === 'any') {
      setAddContexts(['any'])
      return
    }
    const current = addContexts.filter((c) => c !== 'any')
    const next = current.includes(ctx) ? current.filter((c) => c !== ctx) : [...current, ctx]
    setAddContexts(next.length ? next : ['any'])
  }

  const handleCreatePhrase = async (e) => {
    e.preventDefault()
    const text = addText.trim()
    if (!text) {
      setError(new Error(t('phrases.errorRequired')))
      return
    }

    setBusy('adding')
    setError(null)
    try {
      let created = await api.createPhrase(text)
      if (addUrgent || (addContexts.length === 1 && addContexts[0] !== 'any') || addContexts.length > 1) {
        created = await api.updatePhrase(created.id, {
          contexts: addContexts,
          urgent: addUrgent,
        })
      }
      setPhrases((prev) => {
        const existingIndex = prev.findIndex((p) => p.id === created.id)
        if (existingIndex >= 0) {
          const next = [...prev]
          next[existingIndex] = { ...prev[existingIndex], ...created }
          return next
        }
        return [...prev, { ...created, enrolled: 0, sample_count: 0, last_used_at: null }]
      })
      setIsAdding(false)
      flashFeedback('phrases.addedSuccess')
    } catch (err) {
      setError(err)
    } finally {
      if (isMounted.current) setBusy(null)
    }
  }

  // --- Edit Phrase ---
  const handleOpenEdit = (phrase) => {
    setEditingPhrase(phrase)
    setEditText(phrase.text)
    setEditContexts(phrase.contexts?.length ? phrase.contexts : ['any'])
    setEditUrgent(Boolean(phrase.urgent))
    setError(null)
  }

  const handleToggleEditContext = (ctx) => {
    if (ctx === 'any') {
      setEditContexts(['any'])
      return
    }
    const current = editContexts.filter((c) => c !== 'any')
    const next = current.includes(ctx) ? current.filter((c) => c !== ctx) : [...current, ctx]
    setEditContexts(next.length ? next : ['any'])
  }

  const handleUpdatePhrase = async (e) => {
    e.preventDefault()
    const text = editText.trim()
    if (!text) {
      setError(new Error(t('phrases.errorRequired')))
      return
    }

    setBusy('updating')
    setError(null)
    try {
      const updated = await api.updatePhrase(editingPhrase.id, {
        text,
        contexts: editContexts,
        urgent: editUrgent,
      })
      setPhrases((prev) =>
        prev.map((p) => (p.id === updated.id ? { ...p, ...updated } : p))
      )
      setEditingPhrase(null)
      flashFeedback('phrases.updatedSuccess')
    } catch (err) {
      setError(err)
    } finally {
      if (isMounted.current) setBusy(null)
    }
  }

  // --- Delete Phrase ---
  const handleOpenDelete = (phrase) => {
    setDeletingPhrase(phrase)
    setError(null)
  }

  const handleConfirmDelete = async () => {
    if (!deletingPhrase) return
    setBusy('deleting')
    setError(null)
    try {
      await api.deletePhrase(deletingPhrase.id)
      setPhrases((prev) => prev.filter((p) => p.id !== deletingPhrase.id))
      setDeletingPhrase(null)
      flashFeedback('phrases.deletedSuccess')
    } catch (err) {
      setError(err)
    } finally {
      if (isMounted.current) setBusy(null)
    }
  }

  // --- Seed Everyday Phrases ---
  const handleLoadDefaults = async () => {
    setBusy('defaults')
    setError(null)
    try {
      const data = await api.loadDefaultPhrases()
      setPhrases(data)
      flashFeedback('phrases.addedSuccess')
    } catch (err) {
      setError(err)
    } finally {
      if (isMounted.current) setBusy(null)
    }
  }

  // --- Filtering & Searching ---
  const query = search.trim().toLowerCase()
  const filteredPhrases = (phrases || []).filter((phrase) => {
    // Search match
    if (query && !phrase.text.toLowerCase().includes(query)) {
      return false
    }
    // Filter match
    if (activeFilter === 'urgent') return Boolean(phrase.urgent)
    if (['home', 'hospital', 'market'].includes(activeFilter)) {
      return phrase.contexts?.includes(activeFilter) || phrase.contexts?.includes('any')
    }
    return true
  })

  const totalCount = phrases?.length || 0
  const urgentCount = phrases?.filter((p) => p.urgent).length || 0

  if (!phrases && busy === 'loading') {
    return (
      <section className="screen narrow">
        <p className="screen-status" role="status">
          {t('app.loading')}
        </p>
      </section>
    )
  }

  return (
    <section className="screen phrases-screen">
      <header className="phrases-header">
        <div className="phrases-header-text">
          <h1>{t('phrases.title')}</h1>
          <p className="muted">{t('phrases.subtitle')}</p>
        </div>

        <button
          type="button"
          className="pill-outline phrases-add-btn"
          onClick={handleOpenAdd}
          disabled={busy !== null}
        >
          <Plus size={18} aria-hidden="true" strokeWidth={1.5} />
          <span>{t('phrases.add')}</span>
        </button>
      </header>

      {/* Summary Chips */}
      {totalCount > 0 && (
        <div className="phrases-summary" aria-label={t('phrases.title')}>
          <span className="summary-pill">
            {t('phrases.total', { count: totalCount })}
          </span>
          {urgentCount > 0 && (
            <span className="summary-pill urgent">
              {t('phrases.urgentCount', { count: urgentCount })}
            </span>
          )}
        </div>
      )}

      {/* Search and Filter Strip */}
      {totalCount > 0 && (
        <div className="phrases-search-section">
          <div className="search-field">
            <Search className="search-icon" size={18} aria-hidden="true" strokeWidth={1.5} />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('phrases.searchPlaceholder')}
              aria-label={t('phrases.searchPlaceholder')}
              disabled={busy === 'loading'}
            />
            {search && (
              <button
                type="button"
                className="search-clear"
                onClick={() => setSearch('')}
                aria-label={t('phrases.searchClear')}
              >
                <X size={16} aria-hidden="true" strokeWidth={1.5} />
              </button>
            )}
          </div>

          <div className="filter-strip" role="radiogroup" aria-label={t('phrases.contextsLabel')}>
            {[
              ['all', 'phrases.filterAll'],
              ['urgent', 'phrases.filterUrgent'],
              ['home', 'phrases.filterHome'],
              ['hospital', 'phrases.filterHospital'],
              ['market', 'phrases.filterMarket'],
            ].map(([fKey, labelKey]) => (
              <button
                key={fKey}
                type="button"
                role="radio"
                aria-checked={activeFilter === fKey}
                className={`filter-chip ${activeFilter === fKey ? 'active' : ''} ${
                  fKey === 'urgent' ? 'urgent-chip' : ''
                }`}
                onClick={() => setActiveFilter(fKey)}
              >
                {t(labelKey)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Notifications and Alerts */}
      <div aria-live="polite">
        {feedback && <p className="notice-banner" role="status">{feedback}</p>}
        <Alert error={error} />
      </div>

      {error && !phrases && (
        <div className="error-actions">
          <button type="button" className="pill-outline" onClick={loadPhrases}>
            <RotateCcw size={16} aria-hidden="true" strokeWidth={1.5} />
            <span>{t('error.retry')}</span>
          </button>
        </div>
      )}

      {/* Add Phrase Drawer/Card */}
      {isAdding && (
        <article className="phrase-modal-card" aria-labelledby="add-phrase-heading">
          <h2 id="add-phrase-heading">{t('phrases.addTitle')}</h2>
          <p className="muted">{t('phrases.addPrompt')}</p>

          <form onSubmit={handleCreatePhrase} className="phrase-form">
            <div className="field">
              <label htmlFor="add-phrase-text">{t('phrases.textLabel')}</label>
              <input
                id="add-phrase-text"
                type="text"
                value={addText}
                onChange={(e) => setAddText(e.target.value)}
                placeholder={t('phrases.textPlaceholder')}
                lang={user?.language}
                autoFocus
                disabled={busy !== null}
              />
            </div>

            <fieldset className="phrase-fieldset">
              <legend>{t('phrases.contextsLabel')}</legend>
              <p className="field-hint">{t('phrases.contextsHelp')}</p>
              <div className="context-pills-row">
                {CONTEXT_OPTIONS.map((ctx) => {
                  const active = addContexts.includes(ctx)
                  return (
                    <button
                      key={ctx}
                      type="button"
                      className={`context-select-pill ${active ? 'active' : ''}`}
                      onClick={() => handleToggleAddContext(ctx)}
                      disabled={busy !== null}
                    >
                      {active && <Check size={14} aria-hidden="true" strokeWidth={2} />}
                      <span>{t(`speak.context_${ctx}`)}</span>
                    </button>
                  )
                })}
              </div>
            </fieldset>

            <label className="urgent-toggle-label">
              <input
                type="checkbox"
                checked={addUrgent}
                onChange={(e) => setAddUrgent(e.target.checked)}
                disabled={busy !== null}
              />
              <span className="urgent-toggle-text">
                <strong>{t('phrases.urgentLabel')}</strong>
                <small className="muted">{t('phrases.urgentHelp')}</small>
              </span>
            </label>

            <div className="actions">
              <button
                type="button"
                className="pill-outline"
                onClick={() => setIsAdding(false)}
                disabled={busy !== null}
              >
                {t('phrases.cancel')}
              </button>
              <Pill type="submit" icon={null} disabled={!addText.trim() || busy !== null}>
                {t(busy === 'adding' ? 'phrases.saving' : 'phrases.save')}
              </Pill>
            </div>
          </form>
        </article>
      )}

      {/* Edit Phrase Drawer/Card */}
      {editingPhrase && (
        <article className="phrase-modal-card" aria-labelledby="edit-phrase-heading">
          <h2 id="edit-phrase-heading">{t('phrases.editTitle')}</h2>

          <form onSubmit={handleUpdatePhrase} className="phrase-form">
            <div className="field">
              <label htmlFor="edit-phrase-text">{t('phrases.textLabel')}</label>
              <input
                id="edit-phrase-text"
                type="text"
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                lang={user?.language}
                autoFocus
                disabled={busy !== null}
              />
            </div>

            <fieldset className="phrase-fieldset">
              <legend>{t('phrases.contextsLabel')}</legend>
              <p className="field-hint">{t('phrases.contextsHelp')}</p>
              <div className="context-pills-row">
                {CONTEXT_OPTIONS.map((ctx) => {
                  const active = editContexts.includes(ctx)
                  return (
                    <button
                      key={ctx}
                      type="button"
                      className={`context-select-pill ${active ? 'active' : ''}`}
                      onClick={() => handleToggleEditContext(ctx)}
                      disabled={busy !== null}
                    >
                      {active && <Check size={14} aria-hidden="true" strokeWidth={2} />}
                      <span>{t(`speak.context_${ctx}`)}</span>
                    </button>
                  )
                })}
              </div>
            </fieldset>

            <label className="urgent-toggle-label">
              <input
                type="checkbox"
                checked={editUrgent}
                onChange={(e) => setEditUrgent(e.target.checked)}
                disabled={busy !== null}
              />
              <span className="urgent-toggle-text">
                <strong>{t('phrases.urgentLabel')}</strong>
                <small className="muted">{t('phrases.urgentHelp')}</small>
              </span>
            </label>

            <div className="actions">
              <button
                type="button"
                className="pill-outline"
                onClick={() => setEditingPhrase(null)}
                disabled={busy !== null}
              >
                {t('phrases.cancel')}
              </button>
              <Pill type="submit" icon={null} disabled={!editText.trim() || busy !== null}>
                {t(busy === 'updating' ? 'phrases.saving' : 'phrases.save')}
              </Pill>
            </div>
          </form>
        </article>
      )}

      {/* Delete Confirmation Modal */}
      {deletingPhrase && (
        <article className="phrase-modal-card danger-card" aria-labelledby="delete-dialog-title">
          <h2 id="delete-dialog-title">
            {t('phrases.deleteConfirm', { text: deletingPhrase.text })}
          </h2>
          <p className="muted">{t('phrases.deleteWarning')}</p>

          <div className="actions">
            <button
              type="button"
              className="pill-outline"
              onClick={() => setDeletingPhrase(null)}
              disabled={busy !== null}
              autoFocus
            >
              {t('phrases.deleteNo')}
            </button>
            <button
              type="button"
              className="pill-outline destructive"
              onClick={handleConfirmDelete}
              disabled={busy !== null}
            >
              <Trash2 size={16} aria-hidden="true" strokeWidth={1.5} />
              <span>{t(busy === 'deleting' ? 'phrases.deleting' : 'phrases.deleteYes')}</span>
            </button>
          </div>
        </article>
      )}

      {/* Empty Library State */}
      {totalCount === 0 && !isAdding && (
        <div className="phrases-empty-state">
          <h2>{t('phrases.empty')}</h2>
          <p className="muted">{t('phrases.emptyBody')}</p>
          <div className="empty-actions">
            <Pill
              icon={null}
              onClick={handleLoadDefaults}
              disabled={busy !== null}
            >
              {t(busy === 'defaults' ? 'phrases.addingDefaults' : 'phrases.addDefaults')}
            </Pill>
            <button
              type="button"
              className="pill-outline"
              onClick={() => go('/app/enroll')}
            >
              {t('phrases.goTeach')}
            </button>
          </div>
        </div>
      )}

      {/* Empty Search State */}
      {totalCount > 0 && filteredPhrases.length === 0 && (
        <div className="phrases-no-search">
          <p>
            {t('phrases.noSearchResults', { query: search || activeFilter })}
          </p>
          <p className="muted">{t('phrases.noSearchBody')}</p>
          <button
            type="button"
            className="pill-outline"
            onClick={() => {
              setSearch('')
              setActiveFilter('all')
            }}
          >
            {t('phrases.searchClear')}
          </button>
        </div>
      )}

      {/* Phrase Cards List */}
      <ul className="phrases-list" aria-label={t('phrases.title')}>
        {filteredPhrases.map((phrase) => {
          const isPlaying = playingText === phrase.text
          return (
            <li key={phrase.id} className="phrase-card">
              <div className="phrase-card-content">
                <div className="phrase-card-header">
                  <span className="phrase-card-text" lang={user?.language}>
                    {phrase.text}
                  </span>
                  <div className="phrase-card-badges">
                    {phrase.urgent && (
                      <span className="urgent-badge" aria-label={t('speak.urgent')}>
                        {t('speak.urgent')}
                      </span>
                    )}
                    {phrase.contexts?.map((ctx) => (
                      <span key={ctx} className="context-tag">
                        {t(`speak.context_${ctx}`)}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="phrase-card-meta">
                  <span
                    className="meta-stat"
                    title={t('phrases.enrolledStatus', {
                      enrolled: phrase.enrolled ?? 0,
                      needed: NEEDED_RECORDINGS,
                    })}
                  >
                    {t('phrases.enrolledStatus', {
                      enrolled: phrase.enrolled ?? 0,
                      needed: NEEDED_RECORDINGS,
                    })}
                  </span>
                  {Boolean(phrase.sample_count) && (
                    <span className="meta-stat">
                      {t('phrases.usesCount', { count: phrase.sample_count })}
                    </span>
                  )}
                </div>
              </div>

              <div className="phrase-card-actions">
                <button
                  type="button"
                  className="icon-pill-btn"
                  onClick={() => handlePlay(phrase.text)}
                  disabled={busy !== null && playingText !== phrase.text}
                  aria-label={t(isPlaying ? 'phrases.stopPlaying' : 'phrases.listen')}
                >
                  {isPlaying ? (
                    <Square size={16} fill="currentColor" aria-hidden="true" />
                  ) : (
                    <Volume2 size={16} aria-hidden="true" strokeWidth={1.5} />
                  )}
                  <span className="action-label">
                    {t(isPlaying ? 'phrases.playing' : 'phrases.listen')}
                  </span>
                </button>

                <button
                  type="button"
                  className="icon-pill-btn"
                  onClick={() => handleOpenEdit(phrase)}
                  disabled={busy !== null}
                  aria-label={`${t('phrases.edit')}: ${phrase.text}`}
                >
                  <Pencil size={15} aria-hidden="true" strokeWidth={1.5} />
                  <span className="action-label">{t('phrases.edit')}</span>
                </button>

                <button
                  type="button"
                  className="icon-pill-btn delete-btn"
                  onClick={() => handleOpenDelete(phrase)}
                  disabled={busy !== null}
                  aria-label={`${t('phrases.delete')}: ${phrase.text}`}
                >
                  <Trash2 size={15} aria-hidden="true" strokeWidth={1.5} />
                  <span className="action-label">{t('phrases.delete')}</span>
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
