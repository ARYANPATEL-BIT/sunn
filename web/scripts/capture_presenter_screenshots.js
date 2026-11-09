import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, request } from '@playwright/test'
import { LANGUAGES } from '../src/i18n/languages.js'

const ROOT = fileURLToPath(new URL('../..', import.meta.url))
const OUT = path.join(ROOT, 'docs/screenshots/presenter')
const BASE = 'http://localhost:7860'
fs.mkdirSync(OUT, { recursive: true })

async function makeUser() {
  const api = await request.newContext({ baseURL: BASE })
  const signup = await api.post('/api/auth/signup', {
    data: {
      name: 'Presenter Demo User',
      email: `presenter-${Date.now()}@example.com`,
      password: 'demo-password-1',
      language: 'en',
      consent: true,
      invite_code: 'shots-invite',
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
  async function takeShot(name, route, viewport, lang = 'en', complete = false) {
    const context = await browser.newContext({
      baseURL: BASE,
      storageState: state,
      viewport,
      reducedMotion: 'reduce',
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
    await page.goto(route)
    await page.waitForSelector('.presenter-bar')

    if (complete) {
      // Navigate to step 5 then finish
      await page.goto('/app/progress')
      await page.waitForSelector('.presenter-bar')
      const finishBtn = page.locator('.presenter-action-btn.primary')
      await finishBtn.click()
      await page.waitForSelector('.presenter-completed-card')
    }

    await page.waitForTimeout(300)
    const filePath = path.join(OUT, name)
    await page.screenshot({ path: filePath, fullPage: false })
    console.log(`Saved: ${name}`)
    await context.close()
  }

  // 1. Desktop captures
  const desktop = { width: 1280, height: 800 }
  await takeShot('desktop-step1-onboarding.png', '/app/onboarding', desktop)
  await takeShot('desktop-step2-phrases.png', '/app/phrases', desktop)
  await takeShot('desktop-step3-speak.png', '/app/speak', desktop)
  await takeShot('desktop-step4-settings.png', '/app/settings', desktop)
  await takeShot('desktop-step5-progress.png', '/app/progress', desktop)
  await takeShot('desktop-completion.png', '/app/progress', desktop, 'en', true)

  // 2. Mobile captures
  const mobile = { width: 375, height: 812 }
  await takeShot('mobile-step1-onboarding.png', '/app/onboarding', mobile)
  await takeShot('mobile-step3-speak.png', '/app/speak', mobile)
  await takeShot('mobile-step5-progress.png', '/app/progress', mobile)

  // 3. Tablet capture
  const tablet = { width: 768, height: 1024 }
  await takeShot('tablet-step2-phrases.png', '/app/phrases', tablet)

  // 4. Ultra-narrow mobile (320px)
  const mobile320 = { width: 320, height: 568 }
  await takeShot('mobile-320px-step1.png', '/app/onboarding', mobile320)

  // 5. 10 Language captures of Presenter Demo Mode
  for (const { code } of LANGUAGES) {
    await takeShot(`lang-${code}-presenter.png`, '/app/speak', desktop, code)
  }

  await browser.close()
  console.log('All presenter screenshots captured successfully!')
}

capture().catch((err) => {
  console.error('Error capturing screenshots:', err)
  process.exit(1)
})
