import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getGoalOptions, getTargetPhrases, speakProgress, NEEDED } from './quickstart.js'

test('getGoalOptions adapts dynamically to total available phrases', () => {
  // 51 available phrases (e.g. Hindi default library)
  assert.deepEqual(getGoalOptions(51), [10, 20, 25, 50, 51])

  // 18 available phrases
  assert.deepEqual(getGoalOptions(18), [10, 18])

  // Exactly 25 available phrases (no duplicate 25)
  assert.deepEqual(getGoalOptions(25), [10, 20, 25])

  // 8 available phrases (< 10)
  assert.deepEqual(getGoalOptions(8), [8])

  // Zero or empty available
  assert.deepEqual(getGoalOptions(0), [10])
})

test('getTargetPhrases prioritizes starter phrases and caps at goal', () => {
  const dummyPhrases = Array.from({ length: 50 }, (_, i) => ({
    id: i + 1,
    text: i === 0 ? 'मदद चाहिए' : i === 1 ? 'दर्द हो रहा है' : `वाक्य ${i + 1}`,
    sample_count: 0,
    enrolled: 0,
  }))

  const target10 = getTargetPhrases(dummyPhrases, 'hi', 10)
  assert.equal(target10.length, 10)
  assert.equal(target10[0].text, 'मदद चाहिए')
  assert.equal(target10[1].text, 'दर्द हो रहा है')

  const target20 = getTargetPhrases(dummyPhrases, 'hi', 20)
  assert.equal(target20.length, 20)
})

test('speakProgress calculates single source of truth for progress', () => {
  // 51 phrases total
  const dummyPhrases = Array.from({ length: 51 }, (_, i) => ({
    id: i + 1,
    text: `Phrase ${i + 1}`,
    sample_count: 0,
    enrolled: 0,
  }))

  // Scenario A: New user choosing 10
  const progress10 = speakProgress(dummyPhrases, 'en', 10)
  assert.equal(progress10.available, 51)
  assert.equal(progress10.total, 10)
  assert.equal(progress10.ready, 0)
  assert.equal(progress10.open, false)
  assert.equal(progress10.percent, 0)
  assert.equal(progress10.nextPhrase.id, 1)

  // Mark 1 phrase ready (3 recordings)
  dummyPhrases[0].sample_count = NEEDED
  const progress10With1 = speakProgress(dummyPhrases, 'en', 10)
  assert.equal(progress10With1.ready, 1)
  assert.equal(progress10With1.total, 10)
  assert.equal(progress10With1.percent, 10)
  assert.equal(progress10With1.nextPhrase.id, 2)

  // Scenario B: User choosing 20 (denominator is 20, NOT 51!)
  const progress20 = speakProgress(dummyPhrases, 'en', 20)
  assert.equal(progress20.available, 51)
  assert.equal(progress20.total, 20)
  assert.equal(progress20.ready, 1)
  assert.equal(progress20.open, false)
  assert.equal(progress20.percent, 5)

  // Scenario C: User choosing All (51)
  const progressAll = speakProgress(dummyPhrases, 'en', 51)
  assert.equal(progressAll.total, 51)
  assert.equal(progressAll.available, 51)

  // Mark all 20 ready
  for (let i = 0; i < 20; i++) {
    dummyPhrases[i].sample_count = NEEDED
  }
  const progress20Done = speakProgress(dummyPhrases, 'en', 20)
  assert.equal(progress20Done.ready, 20)
  assert.equal(progress20Done.total, 20)
  assert.equal(progress20Done.open, true)
  assert.equal(progress20Done.percent, 100)
})
