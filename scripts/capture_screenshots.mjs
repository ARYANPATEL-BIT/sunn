import fs from 'node:fs'
import path from 'node:path'
import { chromium } from '../web/node_modules/@playwright/test/index.mjs'

const BASE_URL = 'http://localhost:7860'
const OUT_DIR = path.resolve('docs/screenshots')

fs.mkdirSync(OUT_DIR, { recursive: true })

async function main() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
  })

  // Fixed mobile viewport: exactly 390x844 with 2x scale for crisp retina rendering
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
  })

  const page = await context.newPage()

  // 1. Landing Screen (logged out)
  console.log('1. Capturing Landing screen...')
  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(OUT_DIR, '01-landing.png'), fullPage: false })

  // 2. Sign In with Demo Account
  console.log('Logging in as demo user...')
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' })
  await page.fill('input[type=email]', 'demo@sunn.app')
  await page.fill('input[type=password]', 'password123')
  await page.click('button[type=submit]')
  await page.waitForURL('**/app/**', { timeout: 10000 })
  console.log('Logged in successfully, URL:', page.url())

  // 3. Onboarding Screen
  console.log('2. Capturing Onboarding screen...')
  await page.goto(`${BASE_URL}/app/onboarding`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(OUT_DIR, '02-onboarding.png'), fullPage: false })

  // Mark onboarded in localStorage so navigating /app/speak doesn't redirect
  await page.evaluate(() => {
    for (let i = 1; i <= 10; i++) {
      localStorage.setItem(`sunn.onboarded.${i}`, 'true')
    }
  })

  // 4. Teach / Enrollment Screen
  console.log('3. Capturing Teach / Enroll screen...')
  await page.goto(`${BASE_URL}/app/enroll`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(OUT_DIR, '03-teach.png'), fullPage: false })

  // 5. Speak Screen (Resting state)
  console.log('4. Capturing Speak screen...')
  await page.goto(`${BASE_URL}/app/speak`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(OUT_DIR, '04-speak.png'), fullPage: false })

  // 6. Speak Screen with Candidate Matches
  console.log('5. Recording and capturing Candidate Matches...')
  const recBtn = page.locator('button.record')
  if (await recBtn.count() > 0) {
    console.log('Tapping record button...')
    await recBtn.click()
    await page.waitForTimeout(1600)
    console.log('Tapping stop button...')
    await recBtn.click()
    await page.waitForSelector('.result, .results', { timeout: 10000 }).catch(() => {})
    await page.waitForTimeout(800)
  }
  await page.screenshot({ path: path.join(OUT_DIR, '05-candidates.png'), fullPage: false })

  // 7. Phrase Library Screen
  console.log('6. Capturing Phrase Library...')
  await page.goto(`${BASE_URL}/app/phrases`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(OUT_DIR, '06-phrases.png'), fullPage: false })

  // 8. Progress Analytics Screen
  console.log('7. Capturing Progress screen...')
  await page.goto(`${BASE_URL}/app/progress`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(OUT_DIR, '07-progress.png'), fullPage: false })

  // 9. Settings Screen
  console.log('8. Capturing Settings screen...')
  await page.goto(`${BASE_URL}/app/settings`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(OUT_DIR, '08-settings.png'), fullPage: false })

  await browser.close()
  console.log('All uniform screenshots captured successfully!')
}

main().catch(err => {
  console.error(err)
  process.exit(1)
})
