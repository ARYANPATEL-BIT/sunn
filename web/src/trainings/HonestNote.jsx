import { useLang } from '../i18n/index.jsx'

export function HonestNote({ className = '' }) {
  const { t } = useLang()
  return (
    <aside className={`trainings-honest-note ${className}`} aria-label={t('trainings.honestNoteLabel')}>
      <div className="trainings-honest-note-inner">
        <span className="trainings-honest-note-label">{t('trainings.honestNoteLabel')}</span>
        <p className="trainings-honest-note-text">{t('trainings.honestNote')}</p>
      </div>
    </aside>
  )
}

// Lesson content is written in English and Hindi only; other interface languages are told so.
export function LessonsLangNote() {
  const { t, lang } = useLang()
  if (lang === 'en' || lang === 'hi') return null
  return <p className="trainings-lang-note">{t('trainings.lessonsLangNote')}</p>
}
