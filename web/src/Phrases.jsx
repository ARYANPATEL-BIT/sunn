import { ChevronRight, Pencil, Plus, RotateCcw, Search, Square, Trash2, Volume2, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import * as api from './api.js'
import { useAuth } from './auth.jsx'
import { useLang } from './i18n/index.jsx'
import { NEEDED, needsRerecord } from './quickstart.js'
import { Alert, Chips, ICON, Pill, Sheet, Toast, useGo } from './ui.jsx'

const CONTEXT_OPTIONS = ['any', 'home', 'hospital', 'market']
const FILTERS = [
  ['all', 'phrases.filterAll'],
  ['urgent', 'phrases.filterUrgent'],
  ['home', 'phrases.filterHome'],
  ['hospital', 'phrases.filterHospital'],
  ['market', 'phrases.filterMarket'],
]

// Three small dots: one filled for each saved recording.
function RecordingDots({ count }) {
  return (
    <span className="dots small" aria-hidden="true">
      {Array.from({ length: NEEDED }, (_, i) => (
        <span key={i} className={i < count ? 'saved' : ''} />
      ))}
    </span>
  )
}

// The text, where it's needed and whether it's urgent: the same form for adding and editing.
function PhraseForm({ id, text, setText, contexts, toggleContext, urgent, setUrgent, onSubmit, onCancel, busy, saving, autoFocusText, children }) {
  const { t } = useLang()
  const { user } = useAuth()
  return (
    <form onSubmit={onSubmit} className="sheet-form">
      {children}
      <div className="group">
        <div className="field-cell">
          <label htmlFor={id} className="field-label">
            {t('phrases.textLabel')}
          </label>
          <input
            id={id}
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            lang={user?.language}
            data-autofocus={autoFocusText || undefined}
            disabled={busy !== null}
          />
        </div>
      </div>

      <fieldset className="group-wrap">
        <legend className="group-title">{t('phrases.contextsLabel')}</legend>
        <div className="chips wrap">
          {CONTEXT_OPTIONS.map((ctx) => (
            <button
              key={ctx}
              type="button"
              className="chip"
              aria-pressed={contexts.includes(ctx)}
              onClick={() => toggleContext(ctx)}
              disabled={busy !== null}
            >
              {t(`speak.context_${ctx}`)}
            </button>
          ))}
        </div>
        <p className="group-footer">{t('phrases.contextsHelp')}</p>
      </fieldset>

      <div className="group">
        <label className="row check-row">
          <input type="checkbox" checked={urgent} onChange={(e) => setUrgent(e.target.checked)} disabled={busy !== null} />
          <span className="row-text">
            <strong className="row-title">{t('phrases.urgentLabel')}</strong>
            <small className="row-sub">{t('phrases.urgentHelp')}</small>
          </span>
        </label>
      </div>

      <div className="actions">
        <button type="button" className="button" onClick={onCancel} disabled={busy !== null}>
          {t('phrases.cancel')}
        </button>
        <Pill type="submit" disabled={!text.trim() || busy !== null}>
          {t(saving ? 'phrases.saving' : 'phrases.save')}
        </Pill>
      </div>
    </form>
  )
}

export default function Phrases() {
  const { t } = useLang()
  const { user } = useAuth()
  const go = useGo()

  const [phrases, setPhrases] = useState(null)
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState('all') // 'all', 'urgent', 'home', 'hospital', 'market'

  // Sheets: adding, and one phrase's details (which can turn into its edit form or delete question)
  const [isAdding, setIsAdding] = useState(false)
  const [addText, setAddText] = useState('')
  const [addContexts, setAddContexts] = useState(['any'])
  const [addUrgent, setAddUrgent] = useState(false)

  const [detailsId, setDetailsId] = useState(null)

  const [editingPhrase, setEditingPhrase] = useState(null)
  const [editText, setEditText] = useState('')
  const [editContexts, setEditContexts] = useState(['any'])
  const [editUrgent, setEditUrgent] = useState(false)

  const [deletingPhrase, setDeletingPhrase] = useState(null)

  // Status & Feedback
  const [busy, setBusy] = useState(null) // 'loading', 'adding', 'updating', 'deleting', 'defaults', 'playing'
  const [playingText, setPlayingText] = useState(null)
  const [error, setError] = useState(null)
  const [feedback, setFeedback] = useState(null) // a string key, worded when shown
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
    setFeedback(msgKey)
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
      await api.say(phraseText, { fallback: true, language: user?.language })
    } catch (e) {
      setError(e)
    } finally {
      if (isMounted.current) {
        setPlayingText(null)
      }
    }
  }

  // --- Details ---
  const handleOpenDetails = (phrase) => {
    setDetailsId(phrase.id)
    setEditingPhrase(null)
    setDeletingPhrase(null)
    setError(null)
  }

  const handleCloseDetails = () => {
    setDetailsId(null)
    setEditingPhrase(null)
    setDeletingPhrase(null)
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
      setError({ kind: 'server', code: 'empty_phrase' })
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
      setError({ kind: 'server', code: 'empty_phrase' })
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
      setPhrases((prev) => prev.map((p) => (p.id === updated.id ? { ...p, ...updated } : p)))
      setEditingPhrase(null)
      setDetailsId(null)
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
      setDetailsId(null)
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
  const sheetOpen = isAdding || detailsId !== null

  if (!phrases && busy === 'loading') {
    return (
      <section className="screen narrow">
        <p className="screen-status" role="status">
          {t('app.loading')}
        </p>
      </section>
    )
  }

  // One phrase's sheet: its details, or the edit form, or the question before deleting it.
  function phraseSheet(phrase) {
    const titleId = `phrase-${phrase.id}-title`
    if (editingPhrase?.id === phrase.id) {
      return (
        <PhraseForm
          id="edit-phrase-text"
          text={editText}
          setText={setEditText}
          contexts={editContexts}
          toggleContext={handleToggleEditContext}
          urgent={editUrgent}
          setUrgent={setEditUrgent}
          onSubmit={handleUpdatePhrase}
          onCancel={() => setEditingPhrase(null)}
          busy={busy}
          saving={busy === 'updating'}
          autoFocusText
        >
          <h2 id={titleId} className="sheet-title">
            {t('phrases.editTitle')}
          </h2>
          <Alert error={error} />
        </PhraseForm>
      )
    }
    if (deletingPhrase?.id === phrase.id) {
      return (
        <div className="confirm">
          <h2 id={titleId} className="sheet-title">
            {t('phrases.deleteConfirm', { text: phrase.text })}
          </h2>
          <p className="sheet-text">{t('phrases.deleteWarning')}</p>
          <Alert error={error} />
          <div className="actions stacked">
            <button type="button" className="button" onClick={() => setDeletingPhrase(null)} disabled={busy !== null} data-autofocus>
              {t('phrases.deleteNo')}
            </button>
            <button type="button" className="button" onClick={handleConfirmDelete} disabled={busy !== null}>
              <Trash2 {...ICON} />
              <span>{t(busy === 'deleting' ? 'phrases.deleting' : 'phrases.deleteYes')}</span>
            </button>
          </div>
        </div>
      )
    }
    const isPlaying = playingText === phrase.text
    const contexts = phrase.contexts?.length ? phrase.contexts : ['any']
    return (
      <div className="details">
        <h2 id={titleId} className="details-title" lang={user?.language}>
          {phrase.text}
        </h2>
        <p className="details-meta">
          <RecordingDots count={Math.min(phrase.sample_count, NEEDED)} />
          <span>{t('phrases.enrolledStatus', { enrolled: Math.min(phrase.sample_count, NEEDED), needed: NEEDED })}</span>
        </p>
        {needsRerecord(phrase) && <p className="note">{t('phrases.rerecordHelp')}</p>}
        <div className="group">
          <div className="row">
            <span className="row-title">{t('phrases.contextsLabel')}</span>
            <span className="row-value">{contexts.map((ctx) => t(`speak.context_${ctx}`)).join(', ')}</span>
          </div>
          {phrase.urgent && (
            <div className="row">
              <span className="row-title">
                <span className="dot-red" aria-hidden="true" /> {t('speak.urgent')}
              </span>
            </div>
          )}
          {phrase.sources?.map((source) => (
            <div key={source} className="row">
              <span className="row-text">
                <span className="row-title">{t(`demo.sourceBadge_${source}`)}</span>
                <span className="row-sub">{t(`demo.sourceDesc_${source}`)}</span>
              </span>
            </div>
          ))}
        </div>
        <Alert error={error} />
        <div className="actions stacked">
          <Pill
            icon={isPlaying ? Square : Volume2}
            onClick={() => handlePlay(phrase.text)}
            disabled={busy !== null && playingText !== phrase.text}
          >
            {t(isPlaying ? 'phrases.stopPlaying' : 'phrases.listen')}
          </Pill>
          <button
            type="button"
            className="button"
            onClick={() => handleOpenEdit(phrase)}
            disabled={busy !== null}
            aria-label={`${t('phrases.edit')}: ${phrase.text}`}
          >
            <Pencil {...ICON} />
            <span>{t('phrases.edit')}</span>
          </button>
          <button
            type="button"
            className="button"
            onClick={() => handleOpenDelete(phrase)}
            disabled={busy !== null}
            aria-label={`${t('phrases.delete')}: ${phrase.text}`}
          >
            <Trash2 {...ICON} />
            <span>{t('phrases.delete')}</span>
          </button>
        </div>
      </div>
    )
  }

  return (
    <section className="screen phrases-screen">
      <header className="screen-header">
        <div>
          <h1 className="large-title">{t('phrases.title')}</h1>
          {totalCount > 0 && (
            <p className="summary">
              <span>{t('phrases.total', { count: totalCount })}</span>
              {urgentCount > 0 && <span>{t('phrases.urgentCount', { count: urgentCount })}</span>}
            </p>
          )}
        </div>
        <button
          type="button"
          className="icon-button add-button"
          onClick={handleOpenAdd}
          disabled={busy !== null}
          aria-label={t('phrases.add')}
          title={t('phrases.add')}
        >
          <Plus {...ICON} />
        </button>
      </header>

      {/* Search and Filter Strip */}
      {totalCount > 0 && (
        <div className="phrases-search">
          <div className="search">
            <Search className="search-icon" {...ICON} />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('phrases.searchPlaceholder')}
              aria-label={t('phrases.searchPlaceholder')}
              disabled={busy === 'loading'}
            />
            {search && (
              <button type="button" className="search-clear" onClick={() => setSearch('')} aria-label={t('phrases.searchClear')}>
                <X {...ICON} />
              </button>
            )}
          </div>

          <Chips
            label={t('phrases.contextsLabel')}
            options={FILTERS.map(([value, labelKey]) => ({ value, label: t(labelKey), dot: value === 'urgent' }))}
            value={activeFilter}
            onChange={setActiveFilter}
          />
        </div>
      )}

      {/* Notifications and Alerts */}
      <div aria-live="polite">
        {feedback && <Toast>{t(feedback)}</Toast>}
        {!sheetOpen && <Alert error={error} />}
      </div>

      {error && !phrases && (
        <div className="actions">
          <button type="button" className="button" onClick={loadPhrases}>
            <RotateCcw {...ICON} />
            <span>{t('error.retry')}</span>
          </button>
        </div>
      )}

      {/* Empty Library State */}
      {totalCount === 0 && !isAdding && (
        <div className="empty-state">
          <h2 className="title-2">{t('phrases.empty')}</h2>
          <p className="lede-sm">{t('phrases.emptyBody')}</p>
          <div className="actions">
            <Pill onClick={handleLoadDefaults} disabled={busy !== null}>
              {t(busy === 'defaults' ? 'phrases.addingDefaults' : 'phrases.addDefaults')}
            </Pill>
            <button type="button" className="button" onClick={() => go('/app/enroll')}>
              {t('phrases.goTeach')}
            </button>
          </div>
        </div>
      )}

      {/* Empty Search State */}
      {totalCount > 0 && filteredPhrases.length === 0 && (
        <div className="empty-state">
          <p className="title-2">
            {t('phrases.noSearchResults', {
              query: search || t(FILTERS.find(([key]) => key === activeFilter)[1]),
            })}
          </p>
          <p className="lede-sm">{t('phrases.noSearchBody')}</p>
          <button
            type="button"
            className="button"
            onClick={() => {
              setSearch('')
              setActiveFilter('all')
            }}
          >
            {t('phrases.searchClear')}
          </button>
        </div>
      )}

      {/* The library: tap a phrase for its details */}
      {filteredPhrases.length > 0 && (
        <ul className="group phrases-list" aria-label={t('phrases.title')}>
          {filteredPhrases.map((phrase) => {
            const recorded = Math.min(phrase.sample_count, NEEDED)
            const contexts = (phrase.contexts || []).filter((ctx) => ctx !== 'any')
            return (
              <li key={phrase.id} className="phrase-card">
                <button type="button" className="row phrase-row" onClick={() => handleOpenDetails(phrase)} aria-haspopup="dialog">
                  <span className="row-text">
                    <span className="phrase-card-text" lang={user?.language}>
                      {phrase.text}
                    </span>
                    <span className="phrase-meta">
                      <RecordingDots count={recorded} />
                      <span>{t('phrases.enrolledStatus', { enrolled: recorded, needed: NEEDED })}</span>
                      {phrase.urgent && (
                        <span className="badge">
                          <span className="dot-red" aria-hidden="true" />
                          {t('speak.urgent')}
                        </span>
                      )}
                      {needsRerecord(phrase) && <span className="badge">{t('phrases.rerecord')}</span>}
                      {phrase.sources?.map((source) => (
                        <span key={source} className="badge">
                          {t(`demo.sourceBadge_${source}`)}
                        </span>
                      ))}
                      {contexts.map((ctx) => (
                        <span key={ctx} className="tag">
                          {t(`speak.context_${ctx}`)}
                        </span>
                      ))}
                    </span>
                  </span>
                  <ChevronRight className="row-chevron" {...ICON} />
                </button>
                <Sheet
                  open={detailsId === phrase.id}
                  onClose={handleCloseDetails}
                  labelledBy={`phrase-${phrase.id}-title`}
                  closable
                >
                  {phraseSheet(phrase)}
                </Sheet>
              </li>
            )
          })}
        </ul>
      )}

      <Sheet open={isAdding} onClose={() => setIsAdding(false)} labelledBy="add-phrase-heading">
        <PhraseForm
          id="add-phrase-text"
          text={addText}
          setText={setAddText}
          contexts={addContexts}
          toggleContext={handleToggleAddContext}
          urgent={addUrgent}
          setUrgent={setAddUrgent}
          onSubmit={handleCreatePhrase}
          onCancel={() => setIsAdding(false)}
          busy={busy}
          saving={busy === 'adding'}
          autoFocusText
        >
          <h2 id="add-phrase-heading" className="sheet-title">
            {t('phrases.addTitle')}
          </h2>
          <p className="sheet-text">{t('phrases.addPrompt')}</p>
          <Alert error={error} />
        </PhraseForm>
      </Sheet>
    </section>
  )
}
