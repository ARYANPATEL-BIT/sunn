import { BreathingStep } from './BreathingStep.jsx'
import { DialogueStep } from './DialogueStep.jsx'
import { IntroTipStep } from './IntroTipStep.jsx'
import { ListenRepeatStep } from './ListenRepeatStep.jsx'
import { MinimalPairsStep } from './MinimalPairsStep.jsx'
import { ReadAloudStep } from './ReadAloudStep.jsx'
import { ReflectStep } from './ReflectStep.jsx'
import { SpeakWithMeStep } from './SpeakWithMeStep.jsx'

export {
  BreathingStep,
  DialogueStep,
  IntroTipStep,
  ListenRepeatStep,
  MinimalPairsStep,
  ReadAloudStep,
  ReflectStep,
  SpeakWithMeStep,
}

export function StepView({ step, lessonId, categoryId }) {
  if (!step) return null
  const isKids = categoryId === 'kids-speaking'
  const isSmoothOrKids = isKids || categoryId === 'smooth-speaking'

  switch (step.type) {
    case 'intro':
    case 'tip':
      return <IntroTipStep step={step} />
    case 'breathing':
      return <BreathingStep step={step} />
    case 'listen_repeat':
      return (
        <ListenRepeatStep
          step={step}
          categoryId={categoryId}
          isKids={isKids}
          isSmoothOrKids={isSmoothOrKids}
        />
      )
    case 'minimal_pairs':
      return <MinimalPairsStep step={step} />
    case 'read_aloud':
      return (
        <ReadAloudStep
          step={step}
          categoryId={categoryId}
          isKids={isKids}
          isSmoothOrKids={isSmoothOrKids}
        />
      )
    case 'dialogue':
      return <DialogueStep step={step} />
    case 'reflect':
      return <ReflectStep step={step} lessonId={lessonId} />
    case 'speak_with_me':
      return (
        <SpeakWithMeStep
          step={step}
          categoryId={categoryId}
          isKids={isKids}
          isSmoothOrKids={isSmoothOrKids}
        />
      )
    default:
      return <IntroTipStep step={step} />
  }
}
