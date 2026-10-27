import { test as base, expect } from '@playwright/test'
import en from '../src/i18n/en.js'
import hi from '../src/i18n/hi.js'
import { wav } from './audio.js'

export { expect, wav }
export const LANGS = ['en', 'hi']
export const INVITE = 'e2e-invite'
export const PASSWORD = 'e2e-password-1'
const STRINGS = { en, hi }

// The same quick-start phrases as src/quickstart.js, for the language the account speaks.
export const QUICK_START = {
  hi: ['मदद चाहिए', 'दर्द हो रहा है', 'पानी चाहिए', 'बाथरूम जाना है', 'दवाई दे दो', 'डॉक्टर को बुलाओ',
    'सांस लेने में तकलीफ़ है', 'भूख लगी है', 'ठंड लग रही है', 'मुझे उठा दो'],
  en: ['I need help', "I'm in pain", 'I need water', 'I need the bathroom', 'Give me my medicine',
    'Call the doctor', "I can't breathe properly", "I'm hungry", 'I feel cold', 'Help me sit up'],
}

// t() as the app does it, for the interface language under test.
export function t(lang, key, vars = {}) {
  const value = STRINGS[lang][key]
  if (value === undefined) throw new Error(`no ${lang} string ${key}`)
  return typeof value === 'string' ? value.replace(/\{(\w+)\}/g, (_, slot) => vars[slot] ?? '') : value
}

// Every test: the interface language (`lang`) is set before the app loads, and the page is
// watched. Console errors and warnings, failed requests and 4xx/5xx answers fail the test,
// unless the test said it expects that status on that path with watch.allow().
export const test = base.extend({
  lang: ['en', { option: true }],
  page: async ({ page, lang }, use) => {
    await page.addInitScript((l) => {
      if (!localStorage.getItem('sunn.lang')) localStorage.setItem('sunn.lang', l)
    }, lang)
    await use(page)
  },
  watch: [
    async ({ page }, use) => {
      const problems = []
      const allowed = []
      const isAllowed = (status, url) => allowed.some((a) => a.status === status && url.includes(a.path))
      page.on('console', (m) => {
        if (!['error', 'warning'].includes(m.type())) return
        // Headless Chrome renders WebGL in software and reads the canvas back to composite it;
        // the app itself never reads pixels (src/SeaLight.jsx), and a real GPU doesn't do this.
        if (/GL Driver Message .*GPU stall due to ReadPixels/.test(m.text())) return
        const status = Number(m.text().match(/status of (\d{3})/)?.[1])
        if (status && isAllowed(status, m.location().url)) return
        problems.push(`console ${m.type()}: ${m.text()} (${m.location().url})`)
      })
      page.on('pageerror', (e) => problems.push(`page error: ${e.message}`))
      page.on('requestfailed', (r) => {
        // A request cut short by leaving the page isn't a failure.
        if (r.url().startsWith('http') && r.failure()?.errorText !== 'net::ERR_ABORTED') {
          problems.push(`request failed: ${r.method()} ${r.url()} ${r.failure()?.errorText}`)
        }
      })
      page.on('response', (r) => {
        if (r.status() >= 400 && !isAllowed(r.status(), r.url())) {
          problems.push(`HTTP ${r.status()}: ${r.request().method()} ${r.url()}`)
        }
      })
      await use({ allow: (status, path) => allowed.push({ status, path }), problems })
      expect(problems, problems.join('\n')).toEqual([])
    },
    { auto: true },
  ],
})

// --- the API, from the page's own context, so the page shares the session cookie

const unique = () => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`

export async function signUp(request, { speaks = 'en', name } = {}) {
  const email = `e2e-${unique()}@example.com`
  const response = await request.post('/api/auth/signup', {
    data: { name: name || (speaks === 'hi' ? 'आशा' : 'Asha'), email, password: PASSWORD, language: speaks,
      consent: true, invite_code: INVITE },
  })
  expect(response.status(), await response.text()).toBe(200)
  const user = await response.json()
  const phrases = await (await request.post('/api/me/phrases/default')).json()
  return { ...user, password: PASSWORD, phrases }
}

export async function enroll(request, phraseId, times = 1, source) {
  for (let i = 0; i < times; i++) {
    const response = await request.post('/api/me/enroll', {
      multipart: {
        phrase_id: String(phraseId),
        ...(source ? { source } : {}),
        audio: { name: 'r.wav', mimeType: 'audio/wav', buffer: wav(1, 300 + i * 40) },
      },
    })
    expect(response.status(), await response.text()).toBe(200)
  }
}

// Records the quick-start phrases 3 times each, so Speak opens.
export async function openSpeak(request, user) {
  for (const text of QUICK_START[user.language]) {
    const phrase = user.phrases.find((p) => p.text === text)
    await enroll(request, phrase.id, 3)
  }
}

export async function recognizeAndConfirm(request, phraseId) {
  const heard = await request.post('/api/me/recognize', {
    multipart: { audio: { name: 'r.wav', mimeType: 'audio/wav', buffer: wav(1, 500) } },
  })
  expect(heard.status()).toBe(200)
  const { sample_id } = await heard.json()
  const confirmed = await request.post('/api/me/confirm', { data: { sample_id, phrase_id: phraseId } })
  expect(confirmed.status()).toBe(200)
}

// Skips the welcome guide for this account, as a returning user would.
export async function markOnboarded(page, user) {
  await page.addInitScript((id) => localStorage.setItem(`sunn.onboarded.${id}`, 'true'), user.id)
}

// Tap the sun, speak (the fake microphone's tone) for a moment, tap again.
export async function record(page, lang, seconds = 1.5) {
  await page.getByRole('button', { name: t(lang, 'sun.tap') }).or(page.getByRole('button', { name: t(lang, 'sun.again') })).click()
  const stop = page.getByRole('button', { name: new RegExp(t(lang, 'sun.stop')) })
  await expect(stop).toBeVisible()
  await page.waitForTimeout(seconds * 1000)
  await stop.click()
}

// No interface text in the other language: Latin words in Hindi mode, Devanagari in English
// mode. Text marked with another lang (the user's own phrases, the EN / हिं toggle, the wordmark)
// is data or a name and is skipped, as are product names and `data`, like the user's name.
const NAMES = new Set(['Sunn', 'Gnani', 'Prisma', 'Timbre', 'WhatsApp', 'English', 'Hindi', 'TORGO',
  'Great', 'Indian', 'AI', 'Internship', 'Challenge']) // the challenge's name
export async function expectNoLeaks(page, lang, data = []) {
  const texts = await page.evaluate(() => {
    const out = []
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
    const own = document.documentElement.lang
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const el = node.parentElement
      const text = node.textContent.trim()
      if (!text || !el || el.closest('script, style, [aria-hidden="true"]')) continue
      const style = getComputedStyle(el)
      if (style.display === 'none' || style.visibility === 'hidden') continue
      const tagged = el.closest('[lang]')
      if (tagged && tagged.lang !== own && tagged !== document.documentElement) continue
      out.push(text)
    }
    return out
  })
  const leaks = []
  for (const text of texts) {
    // Email addresses and anything in “quotes” (a phrase, what Prisma heard) are data.
    let stripped = text.replace(/[\w.+-]+@[\w.-]+/g, '').replace(/“[^”]*”/g, '')
    for (const value of data) stripped = stripped.replaceAll(value, '')
    if (lang === 'hi') {
      const words = (stripped.match(/[A-Za-z][A-Za-z'’]+/g) || []).filter((w) => !NAMES.has(w))
      if (words.length) leaks.push(`${text}  [${words.join(', ')}]`)
    } else if (/[ऀ-ॿ]/.test(stripped)) {
      leaks.push(text)
    }
  }
  expect(leaks, `text in the wrong language on ${page.url()}:\n${leaks.join('\n')}`).toEqual([])
}

// The card of the phrase with exactly this text (पानी चाहिए, not गरम पानी चाहिए).
export const phraseCard = (page, text) =>
  page.locator('.phrase-card').filter({ has: page.locator('.phrase-card-text').getByText(text, { exact: true }) })

// Answers the next request to `path` with an API refusal, for checking how the app words it
// without tripping the server's real limits (5 wrong invite codes from one address lock sign-up
// for 15 minutes, for every test that runs after).
export async function refuseOnce(page, watch, path, status, body) {
  watch.allow(status, path)
  await page.route(`**${path}`, (route) =>
    route.fulfill({ status, contentType: 'application/json', body: JSON.stringify({ message: 'faked', ...body }) }),
    { times: 1 })
}
