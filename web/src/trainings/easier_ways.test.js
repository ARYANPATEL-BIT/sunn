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
