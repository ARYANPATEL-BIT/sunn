const BASE = import.meta.env.VITE_API_URL || '/api'

async function request(path, options) {
  const res = await fetch(BASE + path, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const error = new Error(body.detail || `HTTP ${res.status}`)
    error.status = res.status
    throw error
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

export const createUser = (name) =>
  post('/users', { name, language: 'hi-IN', consent: true }).then((r) => r.json())

export const loadDefaultPhrases = (userId) => post(`/users/${userId}/phrases/default`).then((r) => r.json())

export const listPhrases = (userId) => request(`/users/${userId}/phrases`).then((r) => r.json())

export const enroll = (userId, phraseId, blob) =>
  upload(`/users/${userId}/enroll`, blob, { phrase_id: phraseId }).then((r) => r.json())

export const recognize = (userId, blob) => upload(`/users/${userId}/recognize`, blob).then((r) => r.json())

// body is { sample_id, phrase_id } or { sample_id, new_text }
export const confirm = (userId, body) => post(`/users/${userId}/confirm`, body).then((r) => r.json())

export const stats = (userId) => request(`/users/${userId}/stats`).then((r) => r.json())

// Speak text aloud with the API's text-to-speech.
export async function say(text) {
  const blob = await post('/speak', { text }).then((r) => r.blob())
  await play(blob)
}

let player = null

// Play an audio blob, stopping whatever was playing before.
export function play(blob) {
  player?.pause()
  const url = URL.createObjectURL(blob)
  player = new Audio(url)
  player.onended = () => URL.revokeObjectURL(url)
  return player.play()
}
