import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, request } from '../web/node_modules/@playwright/test/index.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')
const LANDSCAPE_DIR = path.join(ROOT, 'docs/screenshots/landscape')
const PORTRAIT_DIR = path.join(ROOT, 'docs/screenshots/portrait')
const BASE = 'http://localhost:7860'

fs.mkdirSync(LANDSCAPE_DIR, { recursive: true })
fs.mkdirSync(PORTRAIT_DIR, { recursive: true })

async function run() {
  console.log('--- Starting Screenshot Showcase Capture ---')
  const api = await request.newContext({ baseURL: BASE })
  const loginRes = await api.post('/api/auth/login', {
    data: { email: 'demo@sunn.app', password: 'password123' }
  })
  if (!loginRes.ok()) {
    throw new Error('Failed to login as demo user: ' + await loginRes.text())
  }
  const user = await loginRes.json()
  const storageState = await api.storageState()
  console.log(`Authenticated as demo user: ${user.name} (id: ${user.id})`)

  const browser = await chromium.launch({
    headless: true,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream']
  })

  // LANDSCAPE CAPTURES (1440 x 1000)
  console.log('\n--- Capturing Landscape Screenshots (1440x1000) ---')
  const lContext = await browser.newContext({
    baseURL: BASE,
    storageState,
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
    reducedMotion: 'reduce'
  })
  await lContext.addInitScript(([id]) => {
    localStorage.setItem('sunn.lang', 'en')
    localStorage.setItem('sunn.theme', 'light')
    localStorage.setItem(`sunn.onboarded.${id}`, 'true')
  }, [user.id])
  const lPage = await lContext.newPage()

  // 1. Landing Desktop
  console.log('Capturing: landing-desktop.png')
  const landingContext = await browser.newContext({
    baseURL: BASE,
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
    reducedMotion: 'reduce'
  })
  const landingPage = await landingContext.newPage()
  await landingPage.goto('/', { waitUntil: 'networkidle' })
  await landingPage.waitForTimeout(600)
  await landingPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'landing-desktop.png'), fullPage: false })

  // 2. How It Works Desktop
  console.log('Capturing: how-it-works-desktop.png')
  await landingPage.goto('/how-it-works', { waitUntil: 'networkidle' })
  await landingPage.waitForTimeout(600)
  await landingPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'how-it-works-desktop.png'), fullPage: false })
  await landingContext.close()

  // 3. Speak Desktop (Rest state with visualizer)
  console.log('Capturing: speak-desktop.png')
  await lPage.goto('/app/speak', { waitUntil: 'networkidle' })
  await lPage.waitForTimeout(600)
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'speak-desktop.png'), fullPage: false })

  // 4. Candidate Matches Desktop
  console.log('Capturing: candidates-desktop.png')
  const recordBtn = lPage.getByRole('button', { name: /tap to speak|speak again/i }).first()
  if (await recordBtn.isVisible()) {
    await recordBtn.click()
    await lPage.waitForTimeout(1200)
    const stopBtn = lPage.getByRole('button', { name: /stop listening/i })
    if (await stopBtn.isVisible()) {
      await stopBtn.click()
      await lPage.waitForTimeout(1000)
    }
  }
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'candidates-desktop.png'), fullPage: false })

  // 5. Phrase Library Desktop
  console.log('Capturing: phrase-library-desktop.png')
  await lPage.goto('/app/phrases', { waitUntil: 'networkidle' })
  await lPage.waitForTimeout(600)
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'phrase-library-desktop.png'), fullPage: false })

  // 6. Training Curriculum Desktop
  console.log('Capturing: training-curriculum-desktop.png')
  await lPage.goto('/trainings', { waitUntil: 'networkidle' })
  await lPage.waitForTimeout(600)
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'training-curriculum-desktop.png'), fullPage: false })

  // 7. Course Overview Desktop
  console.log('Capturing: course-overview-desktop.png')
  await lPage.goto('/trainings/smooth-speaking/easy-starts', { waitUntil: 'networkidle' })
  await lPage.waitForTimeout(600)
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'course-overview-desktop.png'), fullPage: false })

  // 8. Listen and Repeat Step Desktop
  console.log('Capturing: listen-repeat-desktop.png')
  await lPage.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1', { waitUntil: 'networkidle' })
  await lPage.waitForTimeout(600)
  for (let s = 0; s < 3; s++) {
    const nextBtn = lPage.locator('.player-nav-btn.primary, .player-next-btn')
    if (await nextBtn.isVisible()) {
      await nextBtn.click()
      await lPage.waitForTimeout(400)
    }
  }
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'listen-repeat-desktop.png'), fullPage: false })

  // 9. Paced Speaking Step Desktop
  console.log('Capturing: paced-speaking-desktop.png')
  await lPage.goto('/trainings/smooth-speaking/easy-starts/easy-starts-2', { waitUntil: 'networkidle' })
  await lPage.waitForTimeout(600)
  for (let s = 0; s < 2; s++) {
    const nextBtn = lPage.locator('.player-nav-btn.primary, .player-next-btn')
    if (await nextBtn.isVisible()) {
      await nextBtn.click()
      await lPage.waitForTimeout(400)
    }
  }
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'paced-speaking-desktop.png'), fullPage: false })

  // 10. Tricky Sounds Desktop
  console.log('Capturing: tricky-sounds-desktop.png')
  await lPage.goto('/trainings', { waitUntil: 'networkidle' })
  await lPage.waitForTimeout(600)
  const trickyCard = lPage.locator('.tricky-sounds-card')
  if (await trickyCard.isVisible()) {
    await trickyCard.scrollIntoViewIfNeeded()
    await lPage.waitForTimeout(300)
  }
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'tricky-sounds-desktop.png'), fullPage: false })

  // 11. Easier Ways Desktop
  console.log('Capturing: easier-ways-desktop.png')
  await lPage.goto('/trainings/easier-ways', { waitUntil: 'networkidle' })
  await lPage.waitForTimeout(600)
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'easier-ways-desktop.png'), fullPage: false })

  // 12. Progress Desktop
  console.log('Capturing: progress-desktop.png')
  await lPage.goto('/app/progress', { waitUntil: 'networkidle' })
  await lPage.waitForTimeout(600)
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'progress-desktop.png'), fullPage: false })

  // 13. Settings Desktop
  console.log('Capturing: settings-desktop.png')
  await lPage.goto('/app/settings', { waitUntil: 'networkidle' })
  await lPage.waitForTimeout(600)
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'settings-desktop.png'), fullPage: false })

  // 14. Presenter Demo Desktop
  console.log('Capturing: presenter-demo-desktop.png')
  await lPage.evaluate(() => {
    localStorage.setItem('sunn.presenter_mode', 'true')
  })
  await lPage.goto('/app/speak', { waitUntil: 'networkidle' })
  await lPage.waitForSelector('.presenter-bar')
  await lPage.waitForTimeout(400)
  await lPage.screenshot({ path: path.join(LANDSCAPE_DIR, 'presenter-demo-desktop.png'), fullPage: false })
  await lContext.close()

  // PORTRAIT CAPTURES (390 x 844)
  console.log('\n--- Capturing Portrait Screenshots (390x844) ---')
  const pContext = await browser.newContext({
    baseURL: BASE,
    storageState,
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    reducedMotion: 'reduce'
  })
  await pContext.addInitScript(([id]) => {
    localStorage.setItem('sunn.lang', 'en')
    localStorage.setItem('sunn.theme', 'light')
    localStorage.setItem(`sunn.onboarded.${id}`, 'true')
  }, [user.id])
  const pPage = await pContext.newPage()

  // 1. Mobile Landing
  console.log('Capturing: landing-mobile.png')
  const pLandingContext = await browser.newContext({
    baseURL: BASE,
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    reducedMotion: 'reduce'
  })
  const pLandingPage = await pLandingContext.newPage()
  await pLandingPage.goto('/', { waitUntil: 'networkidle' })
  await pLandingPage.waitForTimeout(600)
  await pLandingPage.screenshot({ path: path.join(PORTRAIT_DIR, 'landing-mobile.png'), fullPage: false })
  await pLandingContext.close()

  // 2. Mobile Speak
  console.log('Capturing: speak-mobile.png')
  await pPage.goto('/app/speak', { waitUntil: 'networkidle' })
  await pPage.waitForTimeout(600)
  await pPage.screenshot({ path: path.join(PORTRAIT_DIR, 'speak-mobile.png'), fullPage: false })

  // 3. Mobile Candidate Matches
  console.log('Capturing: candidate-matches-mobile.png')
  const pRecordBtn = pPage.getByRole('button', { name: /tap to speak|speak again/i }).first()
  if (await pRecordBtn.isVisible()) {
    await pRecordBtn.click()
    await pPage.waitForTimeout(1200)
    const stopBtn = pPage.getByRole('button', { name: /stop listening/i })
    if (await stopBtn.isVisible()) {
      await stopBtn.click()
      await pPage.waitForTimeout(1000)
    }
  }
  await pPage.screenshot({ path: path.join(PORTRAIT_DIR, 'candidate-matches-mobile.png'), fullPage: false })

  // 4. Mobile Phrase Library
  console.log('Capturing: phrase-library-mobile.png')
  await pPage.goto('/app/phrases', { waitUntil: 'networkidle' })
  await pPage.waitForTimeout(600)
  await pPage.screenshot({ path: path.join(PORTRAIT_DIR, 'phrase-library-mobile.png'), fullPage: false })

  // 5. Mobile Training Curriculum
  console.log('Capturing: training-curriculum-mobile.png')
  await pPage.goto('/trainings', { waitUntil: 'networkidle' })
  await pPage.waitForTimeout(600)
  await pPage.screenshot({ path: path.join(PORTRAIT_DIR, 'training-curriculum-mobile.png'), fullPage: false })

  // 6. Mobile Lesson Player
  console.log('Capturing: lesson-player-mobile.png')
  await pPage.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1', { waitUntil: 'networkidle' })
  await pPage.waitForTimeout(600)
  for (let s = 0; s < 3; s++) {
    const nextBtn = pPage.locator('.player-nav-btn.primary, .player-next-btn')
    if (await nextBtn.isVisible()) {
      await nextBtn.click()
      await pPage.waitForTimeout(400)
    }
  }
  await pPage.screenshot({ path: path.join(PORTRAIT_DIR, 'lesson-player-mobile.png'), fullPage: false })

  // 7. Mobile Easier Ways
  console.log('Capturing: easier-ways-mobile.png')
  await pPage.goto('/trainings/easier-ways', { waitUntil: 'networkidle' })
  await pPage.waitForTimeout(600)
  await pPage.screenshot({ path: path.join(PORTRAIT_DIR, 'easier-ways-mobile.png'), fullPage: false })

  // 8. Mobile Progress
  console.log('Capturing: progress-mobile.png')
  await pPage.goto('/app/progress', { waitUntil: 'networkidle' })
  await pPage.waitForTimeout(600)
  await pPage.screenshot({ path: path.join(PORTRAIT_DIR, 'progress-mobile.png'), fullPage: false })

  // 9. Mobile Settings
  console.log('Capturing: settings-mobile.png')
  await pPage.goto('/app/settings', { waitUntil: 'networkidle' })
  await pPage.waitForTimeout(600)
  await pPage.screenshot({ path: path.join(PORTRAIT_DIR, 'settings-mobile.png'), fullPage: false })

  // 10. Mobile Presenter Demo
  console.log('Capturing: presenter-demo-mobile.png')
  await pPage.evaluate(() => {
    localStorage.setItem('sunn.presenter_mode', 'true')
  })
  await pPage.goto('/app/speak', { waitUntil: 'networkidle' })
  await pPage.waitForSelector('.presenter-bar')
  await pPage.waitForTimeout(400)
  await pPage.screenshot({ path: path.join(PORTRAIT_DIR, 'presenter-demo-mobile.png'), fullPage: false })

  await pContext.close()
  await browser.close()
  console.log('\n--- All showcase screenshots successfully captured! ---')
}

run().catch((err) => {
  console.error('Screenshot capture failed:', err)
  process.exit(1)
})
