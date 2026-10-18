const BASE = import.meta.env.VITE_API_URL || '/api'

// Every failure becomes an Error with a kind the screens turn into a direction:
// offline (our server can't be reached), gnani (Prisma/Timbre failed), server (anything else).
function apiError(kind, detail, status) {
  const error = new Error(detail || kind)
  error.kind = kind
  error.status = status
  return error
}

async function request(path, options) {
  let res
  try {
    res = await fetch(BASE + path, options)
  } catch {
    throw apiError('offline')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    // The dev proxy answers 502 with an empty body when the API isn't running.
    if (!body) throw apiError(res.status >= 502 ? 'offline' : 'server', null, res.status)
    throw apiError(body.source === 'gnani' ? 'gnani' : 'server', body.detail, res.status)
  }
  return res
}

const post = (path, body) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

function upload(path, blob, fields = {}) {
  const form = new FormData()
  for (const [key, value] of Object.entries(fields)) form.append(key, value)
  form.append('audio', blob, 'recording')
  return request(path, { method: 'POST', body: form })
}

export const createUser = (name) => post('/users', { name, language: 'hi', consent: true }).then((r) => r.json())

export const loadDefaultPhrases = (userId) => post(`/users/${userId}/phrases/default`).then((r) => r.json())

// [{ id, text, enrolled }]: enrolled is the number of saved enrollment recordings
export const listPhrases = (userId) => request(`/users/${userId}/phrases`).then((r) => r.json())

export const enroll = (userId, phraseId, blob) =>
  upload(`/users/${userId}/enroll`, blob, { phrase_id: phraseId }).then((r) => r.json())

export const recognize = (userId, blob) => upload(`/users/${userId}/recognize`, blob).then((r) => r.json())

// body is { sample_id, phrase_id } or { sample_id, new_text }
export const confirm = (userId, body) => post(`/users/${userId}/confirm`, body).then((r) => r.json())

export const stats = (userId) => request(`/users/${userId}/stats`).then((r) => r.json())

// Speak text aloud with Gnani Timbre (through the API).
export async function say(text) {
  const blob = await post('/speak', { text }).then((r) => r.blob())
  await play(blob)
}

let player = null

// Play an audio blob, stopping whatever was playing before.
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
