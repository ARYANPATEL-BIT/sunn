import assert from 'node:assert/strict'
import { test } from 'node:test'

// Helper testing syllable counting and pacing math
function countSyllables(word) {
  if (!word) return 1
  const clean = word.toLowerCase().trim()
  const devanagari = clean.match(/[\u0904-\u0914\u093e-\u094c\u0902\u0903]/g)
  if (devanagari && devanagari.length > 0) return devanagari.length
  const normalized = clean.length > 3 ? clean.replace(/e$/, '') : clean
  const latin = normalized.match(/[aeiouy]+/gi)
  if (latin && latin.length > 0) return Math.max(1, latin.length)
  return 1
}

function calculatePacedRate(wpm, wordsCount, audioDuration) {
  const baseWpm = Math.max(25, Math.round((wordsCount * 60) / (audioDuration || 2.0)))
  return Math.max(0.5, Math.min(2.0, wpm / baseWpm))
}

function calculateWordPause(wpm) {
  return Math.max(250, Math.round((60000 / wpm) * 0.45))
}

function computeActiveWordIndex(elapsedSec, totalDuration, words) {
  if (totalDuration <= 0) return words.length
  const progress = Math.min(1.0, Math.max(0.0, elapsedSec / totalDuration))
  if (progress >= 1.0) return words.length

  const syllables = words.map(countSyllables)
  const totalSyllables = syllables.reduce((a, b) => a + b, 0) || 1

  let cumulative = 0
  for (let i = 0; i < words.length; i++) {
    const startProg = cumulative / totalSyllables
    cumulative += syllables[i]
    const endProg = cumulative / totalSyllables
    if (progress >= startProg && progress < endProg) {
      return i
    }
  }
  return words.length
}

test('countSyllables accurately counts Devanagari and Latin syllables', () => {
  // Devanagari
  assert.equal(countSyllables('पानी'), 2)
  assert.equal(countSyllables('मदद'), 1) // default 1 if no matras
  assert.equal(countSyllables('चाहिए'), 3)

  // Latin
  assert.equal(countSyllables('water'), 2)
  assert.equal(countSyllables('please'), 1) // 'ea', 'e' -> latin vowel sequence
  assert.equal(countSyllables('communication'), 5)
})

test('calculatePacedRate clamps playbackRate between 0.5 and 2.0', () => {
  const wordsCount = 4
  const audioDuration = 2.0 // baseWpm = (4 * 60) / 2 = 120 WPM

  // 60 WPM -> 60 / 120 = 0.5x
  assert.equal(calculatePacedRate(60, wordsCount, audioDuration), 0.5)

  // 120 WPM -> 120 / 120 = 1.0x
  assert.equal(calculatePacedRate(120, wordsCount, audioDuration), 1.0)

  // 240 WPM -> 240 / 120 = 2.0x (max clamp)
  assert.equal(calculatePacedRate(240, wordsCount, audioDuration), 2.0)

  // 20 WPM -> clamped to 0.5x
  assert.equal(calculatePacedRate(20, wordsCount, audioDuration), 0.5)
})

test('calculateWordPause scales inversely with WPM', () => {
  // Slower WPM produces longer pause
  const pause40 = calculateWordPause(40)
  const pause60 = calculateWordPause(60)
  const pause100 = calculateWordPause(100)

  assert.ok(pause40 > pause60)
  assert.ok(pause60 > pause100)
  assert.ok(pause100 >= 250) // Minimum floor
})

test('computeActiveWordIndex synchronizes smoothly with audio progress', () => {
  const words = ['Can', 'I', 'have', 'some', 'water?']
  const duration = 2.5 // seconds

  // Start of audio
  assert.equal(computeActiveWordIndex(0.0, duration, words), 0)

  // Progression through all words sequentially
  const seenIndices = new Set()
  const step = 0.05
  for (let t = 0; t < duration; t += step) {
    const idx = computeActiveWordIndex(t, duration, words)
    seenIndices.add(idx)
  }

  // All 5 words must be visited sequentially
  for (let i = 0; i < words.length; i++) {
    assert.ok(seenIndices.has(i), `Word index ${i} was not highlighted`)
  }

  // At or past audio completion, index is words.length (cleared highlight)
  assert.equal(computeActiveWordIndex(2.5, duration, words), words.length)
  assert.equal(computeActiveWordIndex(3.0, duration, words), words.length)
})

test('computeActiveWordIndex handles pauses and resumes deterministically', () => {
  const words = ['Water,', 'please']
  const duration = 2.0

  // Pause at 0.5s
  const pausedIndex = computeActiveWordIndex(0.5, duration, words)
  assert.equal(pausedIndex, 0)

  // While paused, position does not change
  assert.equal(computeActiveWordIndex(0.5, duration, words), pausedIndex)

  // Resume from 0.5s to 1.5s
  const resumedIndex = computeActiveWordIndex(1.5, duration, words)
  assert.equal(resumedIndex, 1)

  // Restart back to 0.0s
  assert.equal(computeActiveWordIndex(0.0, duration, words), 0)
})
