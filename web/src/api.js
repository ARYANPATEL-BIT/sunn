// Relative, so the browser stays on the dev server's one https origin; Vite proxies /api to
// the API. The session is an httpOnly cookie the browser sends by itself.
export const BASE = '/api'

// Fired when any call finds the session gone (expired, or signed out elsewhere); auth.jsx listens.
export const SIGNED_OUT = 'sunn:signed-out'

// Every failure becomes an Error with a kind the screens turn into a direction:
// offline (our server can't be reached), gnani (Prisma/Timbre failed), server (anything else).
// code is the API's reason for a refusal (bad_login, email_taken, not_logged_in…), when it gives one.
// Every API error is { error: code, message } (docs/API.md).
const GNANI_CODES = ['gnani_unreachable', 'gnani_rejected', 'credit_limit_reached', 'daily_cap_reached']

function apiError(kind, message, status, body) {
  const error = new Error(message || kind)
  error.kind = kind
  error.status = status
  error.code = body?.error
  error.retryAfter = body?.retry_after
  return error
}

async function request(path, options = {}) {
  let res
  const config = {
    credentials: 'include',
    ...options,
  }
  try {
    res = await fetch(BASE + path, config)
  } catch {
    throw apiError('offline')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    // The dev proxy answers 502 with an empty body when the API isn't running.
    if (!body) throw apiError(res.status >= 502 ? 'offline' : 'server', null, res.status)
    if (body.error === 'not_logged_in') dispatchEvent(new Event(SIGNED_OUT))
    throw apiError(GNANI_CODES.includes(body.error) ? 'gnani' : 'server', body.message, res.status, body)
  }
  return res
}

const json = (res) => res.json()

const post = (path, body) =>
  request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

const patch = (path, body) =>
  request(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

const del = (path) => request(path, { method: 'DELETE' })

function upload(path, blob, fields = {}) {
  const form = new FormData()
  for (const [key, value] of Object.entries(fields)) {
    if (value !== undefined && value !== null) {
      form.append(key, value)
    }
  }
  form.append('audio', blob, 'recording')
  return request(path, { method: 'POST', body: form })
}

// --- Authentication and Account ---

// Server configuration (e.g. whether invite_required is true)
export const config = () => request('/config').then(json)
export const googleConfig = () => request('/auth/google/config').then(json)

// language is the language the person speaks: one of the ten codes in i18n/languages.js
export const signup = (body) => post('/auth/signup', { ...body, consent: true }).then(json)
export const login = (email, password) => post('/auth/login', { email, password }).then(json)
export const authGoogle = (data) => post('/auth/google', data).then(json)
export const logout = () => post('/auth/logout').then(json)

// The signed-in user, or null when there is no session (401). Other failures throw.
export const me = () =>
  request('/auth/me')
    .then(json)
    .catch((e) => {
      if (e.status === 401) return null
      throw e
    })

// Any of use_own_voice, caregiver_name, caregiver_phone, language (the language the person speaks)
export const updateMe = (changes) => patch('/me', changes).then(json)

// Deletes the account, its phrases, recordings, transcripts and cloned voice
export const deleteAccount = () => del('/me').then(json)

// --- Own-Voice Controls (Voice Cloning) ---

// Clone user's voice from 5-30s audio recording with explicit consent
export const setVoice = (file) => upload('/me/voice', file, { consent: 'true' }).then(json)

// Forget the cloned voice, its embedding, cache and phrases spoken in it
export const deleteVoice = () => del('/me/voice').then(json)

// --- Phrase Management ---

// [{ id, text, contexts, urgent, language, enrolled, sample_count, last_used_at, sources }]
export const listPhrases = () => request('/me/phrases').then(json)

// Add the default everyday phrases in the user's language
export const loadDefaultPhrases = () => post('/me/phrases/default').then(json)

// Create a new phrase: { text }
export const createPhrase = (text) => post('/me/phrases', { text }).then(json)

// Update a phrase: changes can include text, contexts (array), urgent (bool)
export const updatePhrase = (phraseId, changes) => patch(`/me/phrases/${phraseId}`, changes).then(json)

// Delete a phrase, its samples, recordings and uses
export const deletePhrase = (phraseId) => del(`/me/phrases/${phraseId}`).then(json)

// --- Enrollment, Recognition and Confirmation ---

// Enroll a phrase sample recording (3 needed per phrase)
export const enroll = (phraseId, blob) => upload('/me/enroll', blob, { phrase_id: phraseId }).then(json)

// Top 3 candidates for a recording. context is 'home', 'hospital' or 'market'; 'any' sends none.
// uiLanguage is the interface's, which the judge's reason comes back in.
export const recognize = (blob, context, uiLanguage = 'en') =>
  upload('/me/recognize', blob, {
    ...(context && context !== 'any' ? { context } : {}),
    ui_language: uiLanguage,
  }).then(json)

// Confirm a recognition result. Accepts:
// - { sample_id, phrase_id }
// - { sample_id, new_text }
// - { sample_id, template_id, slot_word_id } (composed candidate)
export const confirm = (body) => post('/me/confirm', body).then(json)

// --- Speech Synthesis and Audio Playback ---

// Synthesize speech to a WAV Blob via Gnani Timbre / cloned voice
export const speak = (text) => post('/speak', { text }).then((r) => r.blob())

// Speaks using the browser's native Web Speech API (window.speechSynthesis)
export function speakBrowserFallback(text, language = 'hi-IN') {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    return Promise.reject(new Error('Browser speech synthesis unavailable'))
  }
  return new Promise((resolve, reject) => {
    stopAudio()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = language
    utterance.onend = () => resolve({ fallback: true })
    utterance.onerror = (e) => {
      if (e.error === 'canceled' || e.error === 'interrupted') {
        resolve({ fallback: true, canceled: true })
      } else {
        reject(e)
      }
    }
    window.speechSynthesis.speak(utterance)
  })
}

// Speak text aloud using the browser Audio player, with optional browser fallback
export async function say(text, options = {}) {
  const playId = ++currentPlayId
  try {
    const blob = await speak(text)
    if (playId !== currentPlayId) return { blob, fallback: false }
    await play(blob, playId)
    return { blob, fallback: false }
  } catch (err) {
    if (options.fallback && typeof window !== 'undefined' && window.speechSynthesis) {
      await speakBrowserFallback(text, `${options.language || 'hi'}-IN`)
      return { blob: null, fallback: true }
    }
    throw err
  }
}

let player = null
let currentUrl = null
let currentPlayId = 0

// Play an audio blob, stopping whatever was playing before
export async function play(blob, playId = null) {
  if (playId !== null && playId !== currentPlayId) return
  stopAudio()
  const url = URL.createObjectURL(blob)
  currentUrl = url
  player = new Audio(url)
  const cleanup = () => {
    if (currentUrl === url) {
      URL.revokeObjectURL(url)
      currentUrl = null
    }
  }
  player.onended = cleanup
  player.onerror = cleanup
  try {
    await player.play()
  } catch (err) {
    cleanup()
    if (err?.name === 'AbortError') return
    throw apiError('playback')
  }
}

// Stop currently playing audio and cancel pending playback
export function stopAudio() {
  currentPlayId++
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }
  if (player) {
    player.pause()
    player.currentTime = 0
    player.onended = null
    player.onerror = null
    player = null
  }
  if (currentUrl) {
    URL.revokeObjectURL(currentUrl)
    currentUrl = null
  }
}

// --- Statistics and Usage ---

// Totals, top 5 phrases, and 8-week clear_without_help_rate trend
export const stats = () => request('/me/stats').then(json)

// --- Trainings ---

// List the categories in order with course counts
export const listTrainingsCategories = () => request('/trainings/categories').then(json)

// Get a single category and its courses
export const getTrainingsCategory = (categoryId) =>
  request(`/trainings/categories/${encodeURIComponent(categoryId)}`).then(json)

// Get a course and its lessons
export const getTrainingsCourse = (courseId) =>
  request(`/trainings/courses/${encodeURIComponent(courseId)}`).then(json)

// Get a single lesson with steps
export const getTrainingsLesson = (lessonId) =>
  request(`/trainings/lessons/${encodeURIComponent(lessonId)}`).then(json)

// Get user trainings progress (courses, resume lesson, totals); returns null when signed out
export const getTrainingsProgress = async () => {
  try {
    const res = await request('/me/trainings/progress')
    return await res.json()
  } catch {
    return null
  }
}

// Save lesson progress: lesson_id, step_index (0-based), completed
export const saveTrainingsProgress = (lessonId, stepIndex, completed = false) =>
  post('/me/trainings/progress', { lesson_id: lessonId, step_index: stepIndex, completed }).then(json)

// Post a feeling reflection on a reflect step
export const postTrainingsReflection = (lessonId, stepId, feeling) =>
  post('/me/trainings/reflect', { lesson_id: lessonId, step_id: stepId, feeling }).then(json)

// Send an attempt for a step
export const postTrainingsAttempt = async (audioBlob, stepId, itemId = null, check = false) => {
  const form = new FormData()
  form.append('audio', audioBlob, 'attempt.wav')
  form.append('step_id', stepId)
  if (itemId) form.append('item_id', itemId)
  form.append('check', String(check))
  const res = await request('/me/trainings/attempts', { method: 'POST', body: form })
  return json(res)
}

// Get sounds the user might like to practise
export const getTrickySounds = () => request('/me/trainings/tricky-sounds').then(json)

// Get easier alternatives for a text
export const getAlternatives = (text, lang) =>
  post('/me/trainings/alternatives', { text, lang }).then(json)

// Fetch audio blob for an audio key
export const fetchAudioBlob = async (audioKey) => {
  if (!audioKey) return null
  const res = await request(`/trainings/audio/${encodeURIComponent(audioKey)}`)
  return res.blob()
}

// Play pre-recorded Timbre audio for an audio_key
export const playAudioKey = async (audioKey) => {
  if (!audioKey) return
  try {
    const blob = await fetchAudioBlob(audioKey)
    if (blob) await play(blob)
  } catch (err) {
    if (err?.name === 'AbortError') return
  }
}

