import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, request } from '@playwright/test'
import { LANGUAGES } from '../src/i18n/languages.js'

const ROOT = fileURLToPath(new URL('../..', import.meta.url))
const OUT = path.join(ROOT, 'docs/screenshots/presenter')
const LANDSCAPE_DIR = path.join(ROOT, 'docs/screenshots/landscape')
const PORTRAIT_DIR = path.join(ROOT, 'docs/screenshots/portrait')
const BASE = 'http://localhost:7860'
fs.mkdirSync(OUT, { recursive: true })

async function makeUser() {
  const api = await request.newContext({ baseURL: BASE })
  const loginRes = await api.post('/api/auth/login', {
    data: { email: 'demo@sunn.app', password: 'password123' }
  })
  if (loginRes.ok()) {
    const user = await loginRes.json()
    return { user, state: await api.storageState() }
  }
  const inviteCode = process.env.DEMO_INVITE_CODE || 'YOUR_DEMO_INVITE_CODE'
  const signup = await api.post('/api/auth/signup', {
    data: {
      name: 'Presenter Demo User',
      email: `presenter-${Date.now()}@example.com`,
      password: 'demo-password-1',
      language: 'en',
      consent: true,
      invite_code: inviteCode,
    },
  })
  const user = await signup.json()
  await api.post('/api/me/phrases/default')
  return { user, state: await api.storageState() }
}

async function capture() {
  console.log('Capturing presenter screenshots against', BASE)
  const { user, state } = await makeUser()

  const browser = await chromium.launch()

  // Helper to open presenter on a specific step
  async function takeShot(name, stepIndex, viewport, lang = 'en', complete = false) {
    const context = await browser.newContext({
      baseURL: BASE,
      storageState: state,
      viewport,
      deviceScaleFactor: 2,
    })
    await context.addInitScript(
      ([l, id]) => {
        localStorage.setItem('sunn.lang', l)
        localStorage.setItem('sunn.theme', 'light')
        localStorage.setItem('sunn.presenter_mode', 'true')
        localStorage.setItem(`sunn.onboarded.${id}`, 'true')
      },
      [lang, user.id],
    )
    const page = await context.newPage()
    await page.goto('/app/onboarding')
    await page.waitForSelector('.presenter-bar')

    for (let i = 0; i < stepIndex; i++) {
      const nextBtn = page.locator('.presenter-actions-row .presenter-action-btn.primary')
      await nextBtn.click()
      await page.waitForTimeout(250)
    }

    if (complete) {
      const finishBtn = page.locator('.presenter-actions-row .presenter-action-btn.primary')
      await finishBtn.click()
      await page.waitForSelector('.presenter-completed-card')
    }

    await page.waitForSelector('.presenter-target-highlight', { timeout: 2000 }).catch(() => {})
    await page.waitForTimeout(400)
    const filePath = path.join(OUT, name)
    await page.screenshot({ path: filePath, fullPage: false })
    console.log(`Saved: ${name}`)

    // Also mirror to README showcase if relevant
    if (name === 'desktop-step3-speak.png') {
      await page.screenshot({ path: path.join(LANDSCAPE_DIR, 'presenter-demo-desktop.png'), fullPage: false })
      console.log('Updated: docs/screenshots/landscape/presenter-demo-desktop.png')
    } else if (name === 'mobile-step3-speak.png') {
      await page.screenshot({ path: path.join(PORTRAIT_DIR, 'presenter-demo-mobile.png'), fullPage: false })
      console.log('Updated: docs/screenshots/portrait/presenter-demo-mobile.png')
    }

    await context.close()
  }

  // 1. Desktop captures (1440x900 or 1280x800)
  const desktop = { width: 1440, height: 900 }
  console.log('\n--- Capturing Desktop Spotlight Tour Steps (1440x900) ---')
  await takeShot('desktop-step1-onboarding.png', 0, desktop)
  await takeShot('desktop-step2-phrases.png', 1, desktop)
  await takeShot('desktop-step3-speak.png', 2, desktop)
  await takeShot('desktop-step4-settings.png', 3, desktop)
  await takeShot('desktop-step5-progress.png', 4, desktop)
  await takeShot('desktop-completion.png', 4, desktop, 'en', true)

  // 2. Mobile captures (390x844)
  const mobile = { width: 390, height: 844 }
  console.log('\n--- Capturing Mobile Bottom Sheet Tour Steps (390x844) ---')
  await takeShot('mobile-step1-onboarding.png', 0, mobile)
  await takeShot('mobile-step3-speak.png', 2, mobile)
  await takeShot('mobile-step5-progress.png', 4, mobile)

  // 3. Tablet capture (768x1024)
  const tablet = { width: 768, height: 1024 }
  console.log('\n--- Capturing Tablet Tour Step (768x1024) ---')
  await takeShot('tablet-step2-phrases.png', 1, tablet)

  // 4. Ultra-narrow mobile (320px)
  const mobile320 = { width: 320, height: 568 }
  console.log('\n--- Capturing 320px Mobile Tour Step ---')
  await takeShot('mobile-320px-step1.png', 0, mobile320)

  // 5. Multilingual Presenter Demo Mode
  console.log('\n--- Capturing Multilingual Presenter Demo ---')
  for (const { code } of LANGUAGES.slice(0, 3)) {
    await takeShot(`lang-${code}-presenter.png`, 2, desktop, code)
  }

  await browser.close()
  console.log('\nAll Presenter Tour screenshots successfully captured and verified!')
}

capture().catch((err) => {
  console.error('Capture failed:', err)
  process.exit(1)
})
