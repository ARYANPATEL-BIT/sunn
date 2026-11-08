import { useState } from 'react'
import * as api from '../../api.js'
import { useAuth } from '../../auth.jsx'
import { useLang } from '../../i18n/index.jsx'
import { Icon } from '../../ui/index.js'

export function ReflectStep({ step, lessonId }) {
  const { user } = useAuth()
  const { t, lang } = useLang()
  const [feeling, setFeeling] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const title = step.title?.[lang] || step.title?.en || t('reflect.title')
  const prompt = step.prompt?.[lang] || step.prompt?.en || ''

  const choices = [
    { id: 'easy', label: t('reflect.easy'), reply: t('reflect.replyEasy') },
    { id: 'okay', label: t('reflect.okay'), reply: t('reflect.replyOkay') },
    { id: 'hard', label: t('reflect.hard'), reply: t('reflect.replyHard') },
  ]

  const handleSelect = async (choiceId) => {
    setFeeling(choiceId)
    if (user && lessonId) {
      setSubmitting(true)
      try {
        await api.postTrainingsReflection(lessonId, step.id, choiceId)
      } catch {
        // Non-blocking
      } finally {
        setSubmitting(false)
      }
    }
  }

  const selectedChoice = choices.find((c) => c.id === feeling)

  return (
    <div className="step-container step-reflect">
      <div className="step-card">
        <h2 className="step-main-title">{title}</h2>
        {prompt && <p className="step-body-text reflect-prompt">{prompt}</p>}

        <div className="reflect-choices-grid">
          {choices.map((choice) => {
            const isSelected = feeling === choice.id
            return (
              <button
                key={choice.id}
                type="button"
                className={`reflect-choice-card ${isSelected ? 'selected' : ''}`}
                onClick={() => handleSelect(choice.id)}
                aria-pressed={isSelected}
                disabled={submitting}
              >
                <span className="choice-indicator" aria-hidden="true">
                  {isSelected && <Icon name="checkCircle" className="choice-check-icon" />}
                </span>
                <span className="choice-label">{choice.label}</span>
              </button>
            )
          })}
        </div>

        {selectedChoice && (
          <div className="reflect-supportive-reply" role="status">
            <p className="reply-text">{selectedChoice.reply}</p>
          </div>
        )}
      </div>
    </div>
  )
}
