// Screenshots of landing, Speak, Phrases and Settings in all ten interface languages at 375px,
// into docs/screenshots/languages/. Starts its own server with GNANI_MOCK on (no Gnani credits)
// and an empty data folder. Build the web app first: `npm run build && node scripts/capture_language_screenshots.js`.
// It also prints any text that overflows its box, so clipping is found without squinting.
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, request } from '@playwright/test'
import { wav } from '../e2e/audio.js'
import { LANGUAGES } from '../src/i18n/languages.js'
import { quickStart } from '../src/quickstart.js'

const ROOT = fileURLToPath(new URL('../..', import.meta.url))
const OUT = path.join(ROOT, 'docs/screenshots/languages')
const PORT = 7862
const BASE = `http://localhost:${PORT}`
const TONE = path.join(os.tmpdir(), 'sunn-shots-tone.wav')
fs.mkdirSync(OUT, { recursive: true })
fs.writeFileSync(TONE, wav(2, 220, 48000))

const server = spawn('uv', ['run', 'src/server.py', '--port', String(PORT)], {
  cwd: ROOT,
  shell: true,
  stdio: 'ignore',
  env: {
    ...process.env,
    GNANI_MOCK: '1',
    LLM_ENABLED: '0',
    RERANKER_ENABLED: '0',
    GOOGLE_CLIENT_ID: '',
    SIGNUPS_PER_IP_PER_HOUR: '100000',
    DATA_DIR: fs.mkdtempSync(path.join(os.tmpdir(), 'sunn-shots-data-')),
  },
})

async function waitForServer() {
  for (let i = 0; i < 120; i++) {
    try {
      if ((await fetch(`${BASE}/health`)).ok) return
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 1000))
  }
  throw new Error('server did not start')
}

// A Hindi speaker with the quick-start phrases recorded, so Speak is open.
async function makeUser() {
  const api = await request.newContext({ baseURL: BASE })
  const signup = await api.post('/api/auth/signup', {
    data: { name: 'आशा', email: `shots-${Date.now()}@example.com`, password: 'shots-password-1', language: 'hi',
      consent: true },
  })
  const user = await signup.json()
  const phrases = await (await api.post('/api/me/phrases/default')).json()
  for (const phrase of quickStart(phrases, 'hi')) {
    for (let i = 0; i < 3; i++) {
      await api.post('/api/me/enroll', {
        multipart: { phrase_id: String(phrase.id), audio: { name: 'r.wav', mimeType: 'audio/wav', buffer: wav(1, 300 + i * 40) } },
      })
    }
  }
  return { user, state: await api.storageState() }
}

// Text wider than its box (clipped or spilling out), and any sideways page scroll.
const overflowing = (page) =>
  page.evaluate(() => {
    const out = []
    if (document.documentElement.scrollWidth > innerWidth + 1) out.push(`page scrolls sideways: ${document.documentElement.scrollWidth}px`)
    for (const el of document.querySelectorAll('body *')) {
      if (!el.childNodes.length || el.closest('[aria-hidden="true"], .visually-hidden, dialog:not([open])')) continue
      const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())
      if (!own || !el.getClientRects().length) continue
      const box = el.getBoundingClientRect()
      if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflowX !== 'visible') {
        out.push(`clipped: <${el.tagName.toLowerCase()} class="${el.className}"> ${el.textContent.trim().slice(0, 40)}`)
      } else if (box.right > innerWidth + 1) {
        out.push(`off screen: <${el.tagName.toLowerCase()} class="${el.className}"> ${el.textContent.trim().slice(0, 40)}`)
      }
    }
    return out
  })

async function run() {
  await waitForServer()
  const { user, state } = await makeUser()
  const browser = await chromium.launch({
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', `--use-file-for-fake-audio-capture=${TONE}`],
  })
  let problems = 0
  for (const { code } of LANGUAGES) {
    const context = await browser.newContext({
      baseURL: BASE,
      storageState: state,
      viewport: { width: 375, height: 812 },
      reducedMotion: 'reduce',
      permissions: ['microphone'],
    })
    await context.addInitScript(
      ([l, id]) => {
        localStorage.setItem('sunn.lang', l)
        localStorage.setItem('sunn.theme', 'light')
        localStorage.setItem(`sunn.onboarded.${id}`, 'true')
      },
      [code, user.id],
    )
    const page = await context.newPage()
    const shoot = async (name) => {
      await page.evaluate(() => document.fonts.ready)
      await page.screenshot({ path: path.join(OUT, `${name}_${code}.png`), fullPage: true })
      const found = await overflowing(page)
      problems += found.length
      console.log(`${name}_${code}.png${found.length ? `\n  ${found.join('\n  ')}` : ''}`)
    }

    await page.goto('/')
    await page.locator('.hero').waitFor()
    await shoot('landing')

    // Speak after one phrase: the readout, the alternates, the band and the push button.
    await page.goto('/app/speak')
    await page.locator('button.record').click()
    await page.waitForTimeout(1500)
    await page.locator('button.record').click()
    await page.locator('.candidate').first().waitFor()
    await shoot('speak')

    await page.goto('/app/phrases')
    await page.locator('.phrase-card').first().waitFor()
    await shoot('phrases')

    await page.goto('/app/settings')
    await page.locator('.settings-screen').waitFor()
    await shoot('settings')
    await context.close()
  }
  await browser.close()
  console.log(`\n${problems} overflow finding(s). Screenshots in ${OUT}`)
}

run()
  .catch((e) => {
    console.error(e)
    process.exitCode = 1
  })
  .finally(() => {
    // uv starts python as a child; on Windows only taskkill /T takes the whole tree down.
    if (process.platform === 'win32') spawn('taskkill', ['/pid', String(server.pid), '/T', '/F'], { stdio: 'ignore' })
    else server.kill()
  })
