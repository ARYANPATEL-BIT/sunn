// Relative, so the browser stays on the dev server's one https origin; Vite proxies /api to
// the API. The session is an httpOnly cookie the browser sends by itself.
const BASE = '/api'

// Fired when any call finds the session gone (expired, or signed out elsewhere); auth.jsx listens.
export const SIGNED_OUT = 'sunn:signed-out'

// Every failure becomes an Error with a kind the screens turn into a direction:
// offline (our server can't be reached), gnani (Prisma/Timbre failed), server (anything else).
// code is the API's reason for a refusal (bad_login, email_taken, not_logged_in…), when it gives one.
// Every API error is { error: code, message } (docs/API.md).
const GNANI_CODES = ['gnani_unreachable', 'gnani_rejected', 'credit_limit_reached']

function apiError(kind, message, status, body) {
  const error = new Error(message || kind)
  error.kind = kind
  error.status = status
  error.code = body?.error
  error.retryAfter = body?.retry_after
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
    if (body.error === 'not_logged_in') dispatchEvent(new Event(SIGNED_OUT))
    throw apiError(GNANI_CODES.includes(body.error) ? 'gnani' : 'server', body.message, res.status, body)
  }
  return res
}

const json = (res) => res.json()

const post = (path, body) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

function upload(path, blob, fields = {}) {
  const form = new FormData()
  for (const [key, value] of Object.entries(fields)) form.append(key, value)
  form.append('audio', blob, 'recording')
  return request(path, { method: 'POST', body: form })
}

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
export const deleteAccount = () => request('/me', { method: 'DELETE' }).then(json)

export const loadDefaultPhrases = () => post('/me/phrases/default').then(json)

// [{ id, text, enrolled }]: enrolled is the number of saved enrollment recordings
export const listPhrases = () => request('/me/phrases').then(json)

export const enroll = (phraseId, blob) => upload('/me/enroll', blob, { phrase_id: phraseId }).then(json)

export const recognize = (blob) => upload('/me/recognize', blob).then(json)

// body is { sample_id, phrase_id } or { sample_id, new_text }
export const confirm = (body) => post('/me/confirm', body).then(json)

export const stats = () => request('/me/stats').then(json)

// Speak text aloud with Gnani Timbre (through the API), in the signed-in user's language.
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
