import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, request } from '@playwright/test'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '../..')
const OUT_DIR = path.join(ROOT, 'docs/screenshots/trainings')
fs.mkdirSync(OUT_DIR, { recursive: true })

const BASE_URL = 'http://localhost:7860'

const VIEWPORTS = [
  { name: '1440', width: 1440, height: 900 },
  { name: '375', width: 375, height: 812 },
]

const THEMES = ['light', 'dark']
const LANGS = ['en', 'hi']

async function setupUser(req, lang) {
  const email = `shots_${lang}_${Date.now()}@example.com`
  await req.post('/api/auth/signup', {
    data: {
      email,
      password: 'e2e-password-1',
      name: lang === 'hi' ? 'आशा' : 'Asha',
      language: lang,
      consent: true,
      invite_code: 'e2e-invite',
    },
  })
  return req.storageState()
}

async function run() {
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      '--autoplay-policy=no-user-gesture-required',
    ],
  })

  const req = await request.newContext({ baseURL: BASE_URL })
  console.log('Setting up test accounts...')
  const states = {
    en: await setupUser(req, 'en'),
    hi: await setupUser(req, 'hi'),
  }

  for (const lang of LANGS) {
    for (const theme of THEMES) {
      for (const vp of VIEWPORTS) {
        console.log(`\nCapturing set: lang=${lang}, theme=${theme}, viewport=${vp.name}`)
        const context = await browser.newContext({
          storageState: states[lang],
          baseURL: BASE_URL,
          viewport: { width: vp.width, height: vp.height },
        })

        const page = await context.newPage()
        await page.addInitScript(
          ({ t, l }) => {
            localStorage.setItem('sunn.theme', t)
            localStorage.setItem('sunn.lang', l)
            document.documentElement.dataset.theme = t
            document.documentElement.lang = l
          },
          { t: theme, l: lang },
        )

        const save = async (name, locator = null) => {
          const filename = `${name}_${lang}_${theme}_${vp.name}.png`
          const filepath = path.join(OUT_DIR, filename)
          if (locator) {
            await locator.screenshot({ path: filepath })
          } else {
            await page.screenshot({ path: filepath, fullPage: false })
          }
          console.log(`  ✓ ${filename}`)
        }

        // 1. Trainings Home
        await page.goto('/trainings')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.category-card')
        await save('trainings_home')

        // 2. Tricky sounds card (scrolled to)
        const trickyCard = page.locator('.tricky-sounds-card')
        if (await trickyCard.isVisible()) {
          await trickyCard.scrollIntoViewIfNeeded()
          await page.waitForTimeout(100)
          await save('tricky_sounds')
        }

        // 3. Category pages
        const categories = [
          'smooth-speaking',
          'clear-sounds',
          'everyday-talk',
          'kids-speaking',
        ]
        for (const cat of categories) {
          await page.goto(`/trainings/${cat}`)
          await page.waitForLoadState('networkidle')
          await page.waitForSelector('.course-card-link')
          await save(`category_${cat.replace(/-/g, '_')}`)
        }

        // 4. Course page (easy-starts)
        await page.goto('/trainings/smooth-speaking/easy-starts')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.lesson-row')
        await save('course_page')

        // 5. Steps
        // Intro step
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1?step=0')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.step-intro-tip')
        await save('step_intro')

        // Breathing step
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1?step=1')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.step-breathing')
        await save('step_breathing')

        // Tip step
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1?step=2')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.step-intro-tip')
        await save('step_tip')

        // Listen repeat step
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1?step=3')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.step-listen-repeat')
        await save('step_listen_repeat')

        // Minimal pairs step
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-2?step=1')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.step-minimal-pairs')
        await save('step_minimal_pairs')

        // Read aloud step
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-2?step=4')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.step-read-aloud')
        await save('step_read_aloud')

        // Dialogue step
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-2?step=5')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.step-dialogue')
        await save('step_dialogue')

        // Speak with me: Choral
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1?step=4')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.step-speak-with-me')
        await save('speak_with_me_choral')

        // Speak with me: Paced
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-2?step=3')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.pace-range-input')
        if (vp.name === '375') {
          await page.locator('.pace-slider-box').scrollIntoViewIfNeeded()
          await page.waitForTimeout(100)
        }
        await save('speak_with_me_paced')

        // Reflect step
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1?step=5')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.reflect-choice-card')
        await save('step_reflect')

        // Check feedback
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1?step=3')
        await page.waitForLoadState('networkidle')
        const recBtn = page.locator('button.record').first()
        if (await recBtn.isVisible()) {
          await recBtn.click()
          await page.waitForTimeout(1200)
          await recBtn.click()
          await page.waitForTimeout(400)
          const checkBtn = page.locator('.check-reading-btn')
          if (await checkBtn.isVisible()) {
            await checkBtn.click()
            await page.waitForSelector('.check-results-stage', { timeout: 5000 })
            const resultsStage = page.locator('.check-results-stage')
            if (await resultsStage.isVisible()) {
              await resultsStage.scrollIntoViewIfNeeded()
              await page.waitForTimeout(150)
            }
            await save('check_feedback')
          }
        }

        // Completion screen
        await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1?done=1')
        await page.waitForLoadState('networkidle')
        await page.waitForSelector('.lesson-done-container')
        await save('lesson_done')

        // Easier ways
        await page.goto('/trainings/easier-ways')
        await page.waitForLoadState('networkidle')
        const searchInput = page.locator('#easier-ways-input')
        await searchInput.fill(lang === 'hi' ? 'शुक्रिया' : 'Thank you')
        await page.locator('.easier-ways-search-btn').click()
        await page.waitForSelector('.alternative-card', { timeout: 5000 })
        await save('easier_ways')

        // Progress tab Trainings section
        await page.goto('/app/progress')
        await page.waitForLoadState('networkidle')
        const progSection = page.locator('.trainings-progress-section')
        if (await progSection.isVisible()) {
          await progSection.scrollIntoViewIfNeeded()
          await page.waitForTimeout(100)
          await save('progress_section')
        }

        await context.close()
      }
    }
  }

  await browser.close()
  console.log('\nAll screenshots captured successfully into docs/screenshots/trainings/')
}

run().catch((e) => {
  console.error(e)
  process.exit(1)
})
