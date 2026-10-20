// Relative, so the browser stays on the dev server's one https origin; Vite proxies /api to
// the API. The session is an httpOnly cookie the browser sends by itself.
export const BASE = '/api'

// Fired when any call finds the session gone (expired, or signed out elsewhere); auth.jsx listens.
export const SIGNED_OUT = 'sunn:signed-out'

// Supported contexts for phrases and recognition ranking (matcher.py)
export const CONTEXTS = ['home', 'hospital', 'market', 'any']

// Supported slot types for building block templates and slot words
export const SLOTS = ['item', 'person', 'place']

// Every failure becomes an Error with a kind the screens turn into a direction:
// offline (our server can't be reached), gnani (Prisma/Timbre failed), server (anything else).
// code is the API's reason for a refusal (bad_login, email_taken, no_session…), when it gives one.
function apiError(kind, detail, status, body) {
  const error = new Error(detail || kind)
  error.kind = kind
  error.status = status
  error.code = body?.code
  error.retryAfter = body?.retry_after
  error.source = body?.source
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
    if (body.code === 'no_session') dispatchEvent(new Event(SIGNED_OUT))
    throw apiError(body.source === 'gnani' ? 'gnani' : 'server', body.detail, res.status, body)
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

// language is the language the person speaks: 'hi' or 'en'
export const signup = (body) => post('/auth/signup', { ...body, consent: true }).then(json)
export const login = (email, password) => post('/auth/login', { email, password }).then(json)
export const logout = () => post('/auth/logout').then(json)

// The signed-in user, or null when there is no session (401). Other failures throw.
export const me = () =>
  request('/auth/me')
    .then(json)
    .catch((e) => {
      if (e.status === 401) return null
      throw e
    })

// Update user settings (use_own_voice, caregiver_name, caregiver_phone)
export const updateMe = (changes) => patch('/me', changes).then(json)
export const updateSettings = updateMe

// Deletes the account, its phrases, recordings, transcripts and cloned voice
export const deleteAccount = () => del('/me').then(json)

// --- Own-Voice Controls (Voice Cloning) ---

// Clone user's voice from 5-30s audio recording with explicit consent
export const setVoice = (blob, consent = true) =>
  upload('/me/voice', blob, { consent: String(consent) }).then(json)
export const uploadVoice = setVoice

// Forget the cloned voice, its embedding, cache and phrases spoken in it
export const deleteVoice = () => del('/me/voice').then(json)

// --- Phrase Management ---

// [{ id, text, contexts, urgent, enrolled, sample_count, last_used_at }]
export const listPhrases = () => request('/me/phrases').then(json)

// Add the default everyday phrases in the user's language
export const loadDefaultPhrases = () => post('/me/phrases/default').then(json)

// Create a new phrase: { text }
export const createPhrase = (text) => post('/me/phrases', { text }).then(json)
export const addPhrase = createPhrase

// Update a phrase: changes can include text, contexts (array), urgent (bool)
export const updatePhrase = (phraseId, changes) => patch(`/me/phrases/${phraseId}`, changes).then(json)

// Delete a phrase, its samples, recordings and uses
export const deletePhrase = (phraseId) => del(`/me/phrases/${phraseId}`).then(json)

// Delete a single recording sample
export const deleteSample = (sampleId) => del(`/me/samples/${sampleId}`).then(json)

// --- Enrollment, Recognition and Confirmation ---

// Enroll a phrase sample recording (3 needed per phrase)
export const enroll = (phraseId, blob) => upload('/me/enroll', blob, { phrase_id: phraseId }).then(json)

// Top 3 candidates for a recording, with optional context ('home', 'hospital', 'market', 'any')
export const recognize = (blob, context = null) =>
  upload('/me/recognize', blob, context ? { context } : {}).then(json)

// Confirm a recognition result. Accepts:
// - { sample_id, phrase_id }
// - { sample_id, new_text }
// - { sample_id, template_id, slot_word_id } (composed candidate)
export const confirm = (body) => post('/me/confirm', body).then(json)

// --- Building Blocks: Slot Words and Templates ---

// List slot words: [{ id, slot, text, enrolled }]
export const listSlotWords = () => request('/me/slot-words').then(json)

// Create a slot word: slot is 'item', 'person', or 'place'
export const createSlotWord = (slot, text) => post('/me/slot-words', { slot, text }).then(json)
export const addSlotWord = createSlotWord

// Delete a slot word and its recordings
export const deleteSlotWord = (slotWordId) => del(`/me/slot-words/${slotWordId}`).then(json)

// Enroll an audio recording for a slot word
export const enrollSlotWord = (slotWordId, blob) =>
  upload(`/me/slot-words/${slotWordId}/enroll`, blob).then(json)

// List templates: [{ id, text, fixed_part, slot, enrolled }]
export const listTemplates = () => request('/me/templates').then(json)

// Create a template: text must contain {item}, {person}, or {place}
export const createTemplate = (text) => post('/me/templates', { text }).then(json)
export const addTemplate = createTemplate

// Delete a template and its recordings
export const deleteTemplate = (templateId) => del(`/me/templates/${templateId}`).then(json)

// Enroll an audio recording for a template's fixed part alone
export const enrollTemplate = (templateId, blob) =>
  upload(`/me/templates/${templateId}/enroll`, blob).then(json)

// --- Speech Synthesis and Audio Playback ---

// Synthesize speech to a WAV Blob via Gnani Timbre / cloned voice
export const speak = (text) => post('/speak', { text }).then((r) => r.blob())
export const synthesize = speak

// Speak text aloud using the browser Audio player
export async function say(text) {
  const blob = await speak(text)
  await play(blob)
  return blob
}

let player = null

// Play an audio blob, stopping whatever was playing before
export async function play(blob) {
  player?.pause()
  const url = URL.createObjectURL(blob)
  player = new Audio(url)
  player.onended = () => URL.revokeObjectURL(url)
  try {
    await player.play()
  } catch {
    throw apiError('playback')
  }
}

// Stop currently playing audio if any
export function stopAudio() {
  if (player) {
    player.pause()
    player.currentTime = 0
  }
}

// --- Statistics and Usage ---

// Totals, top 5 phrases, and 8-week clear_without_help_rate trend
export const stats = () => request('/me/stats').then(json)
export const getStats = stats

// Usage counts against GNANI_CALL_LIMIT (owner account only)
export const usage = () => request('/me/usage').then(json)
export const getUsage = usage
