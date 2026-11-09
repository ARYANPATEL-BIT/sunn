import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../web/node_modules/@playwright/test/index.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BASE_URL = 'http://localhost:7860'
const OUT_DIR = path.resolve(__dirname, '../docs/screenshots/responsive-qa')

fs.mkdirSync(OUT_DIR, { recursive: true })

async function captureViewport(browser, { name, width, height }) {
  console.log(`\n--- Capturing viewport: ${name} (${width}x${height}) ---`)
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 2,
  })

  const page = await context.newPage()

  // 1. Landing Screen
  console.log(`[${name}] Capturing Landing screen...`)
  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await page.screenshot({ path: path.join(OUT_DIR, `${name}-01-landing.png`), fullPage: false })

  // If mobile/tablet, capture open navigation drawer
  if (width < 1024) {
    const toggle = page.locator('.mobile-nav-toggle')
    if (await toggle.isVisible()) {
      await toggle.click()
      await page.waitForTimeout(400)
      await page.screenshot({ path: path.join(OUT_DIR, `${name}-01b-landing-drawer.png`), fullPage: false })
      const closeBtn = page.locator('.close-drawer-btn')
      if (await closeBtn.isVisible()) {
        await closeBtn.click()
        await page.waitForTimeout(300)
      }
    }
  }

  // 2. Sign In Screen
  console.log(`[${name}] Capturing Login screen...`)
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(OUT_DIR, `${name}-02-login.png`), fullPage: false })

  // Authenticate as demo user
  console.log(`[${name}] Authenticating as demo user...`)
  await page.fill('input[type=email]', 'demo@sunn.app')
  await page.fill('input[type=password]', 'password123')
  await page.click('button[type=submit]')
  await page.waitForURL('**/app/**', { timeout: 10000 }).catch(() => {})
  await page.waitForTimeout(600)

  // Mark all onboarded in localStorage
  await page.evaluate(() => {
    for (let i = 1; i <= 50; i++) {
      localStorage.setItem(`sunn.onboarded.${i}`, 'true')
    }
  })

  // 3. Speak Screen
  console.log(`[${name}] Capturing Speak screen...`)
  await page.goto(`${BASE_URL}/app/speak`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await page.screenshot({ path: path.join(OUT_DIR, `${name}-03-speak.png`), fullPage: false })

  // 4. Phrase Library Screen
  console.log(`[${name}] Capturing Phrase Library...`)
  await page.goto(`${BASE_URL}/app/phrases`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await page.screenshot({ path: path.join(OUT_DIR, `${name}-04-phrases.png`), fullPage: false })

  // 5. Trainings Home Screen
  console.log(`[${name}] Capturing Trainings Home...`)
  await page.goto(`${BASE_URL}/trainings`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await page.screenshot({ path: path.join(OUT_DIR, `${name}-05-trainings-home.png`), fullPage: false })

  // 6. Course Page
  console.log(`[${name}] Capturing Course Page...`)
  await page.goto(`${BASE_URL}/trainings/smooth-speaking/easy-starts`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await page.screenshot({ path: path.join(OUT_DIR, `${name}-06-course-page.png`), fullPage: false })

  // 7. Lesson Player
  console.log(`[${name}] Capturing Lesson Player...`)
  await page.goto(`${BASE_URL}/trainings/smooth-speaking/easy-starts/easy-starts-1`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await page.screenshot({ path: path.join(OUT_DIR, `${name}-07-lesson-player.png`), fullPage: false })

  // 8. Easier Ways Screen
  console.log(`[${name}] Capturing Easier Ways...`)
  await page.goto(`${BASE_URL}/trainings/easier-ways`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await page.screenshot({ path: path.join(OUT_DIR, `${name}-08-easier-ways.png`), fullPage: false })

  // 9. Progress Dashboard
  console.log(`[${name}] Capturing Progress Dashboard...`)
  await page.goto(`${BASE_URL}/app/progress`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await page.screenshot({ path: path.join(OUT_DIR, `${name}-09-progress.png`), fullPage: false })

  // 10. Settings Screen
  console.log(`[${name}] Capturing Settings Screen...`)
  await page.goto(`${BASE_URL}/app/settings`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await page.screenshot({ path: path.join(OUT_DIR, `${name}-10-settings.png`), fullPage: false })

  await context.close()
}

async function main() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
  })

  // 1. Ultra-compact mobile (320x568 iPhone SE 1st gen)
  await captureViewport(browser, { name: 'mobile-compact', width: 320, height: 568 })

  // 2. Standard mobile (390x844 iPhone 13/14)
  await captureViewport(browser, { name: 'mobile', width: 390, height: 844 })

  // 3. Landscape mobile (844x390)
  await captureViewport(browser, { name: 'landscape', width: 844, height: 390 })

  // 4. Tablet portrait (768x1024 iPad Mini)
  await captureViewport(browser, { name: 'tablet', width: 768, height: 1024 })

  // 5. Desktop standard (1440x900)
  await captureViewport(browser, { name: 'desktop', width: 1440, height: 900 })

  await browser.close()
  console.log('\nAll responsive screenshot captures completed successfully in docs/screenshots/responsive-qa!')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
