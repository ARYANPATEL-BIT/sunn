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
