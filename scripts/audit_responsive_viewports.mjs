import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../web/node_modules/@playwright/test/index.mjs'

const BASE_URL = 'http://localhost:7860'

const VIEWPORTS = [
  { id: 'V1', name: 'iPhone SE (320x568)', width: 320, height: 568 },
  { id: 'V2', name: 'Galaxy S20 (360x800)', width: 360, height: 800 },
  { id: 'V3', name: 'iPhone 14 (390x844)', width: 390, height: 844 },
  { id: 'V4', name: 'Pixel 7 (412x915)', width: 412, height: 915 },
  { id: 'V5', name: 'iPad Mini (768x1024)', width: 768, height: 1024 },
  { id: 'V6', name: 'iPad Air (820x1180)', width: 820, height: 1180 },
  { id: 'V7', name: 'iPad Landscape (1024x768)', width: 1024, height: 768 },
  { id: 'V8', name: 'iPad Pro 12.9 (1024x1366)', width: 1024, height: 1366 },
  { id: 'V9', name: 'Laptop 13in (1280x800)', width: 1280, height: 800 },
  { id: 'V10', name: 'Budget Laptop (1366x768)', width: 1366, height: 768 },
  { id: 'V11', name: 'MacBook Air (1440x900)', width: 1440, height: 900 },
  { id: 'V12', name: 'Modern Laptop (1536x864)', width: 1536, height: 864 },
  { id: 'V13', name: 'Full HD (1920x1080)', width: 1920, height: 1080 },
  { id: 'L1', name: 'iPhone Landscape (844x390)', width: 844, height: 390 },
  { id: 'L2', name: 'Pixel Landscape (915x412)', width: 915, height: 412 },
  { id: 'L3', name: 'Netbook Landscape (1024x600)', width: 1024, height: 600 },
]

const ROUTES = [
  { path: '/', auth: false, name: 'Landing' },
  { path: '/login', auth: false, name: 'Login' },
  { path: '/signup', auth: false, name: 'Signup' },
  { path: '/trainings', auth: false, name: 'Trainings Home' },
  { path: '/trainings/smooth-speaking', auth: false, name: 'Category Smooth Speaking' },
  { path: '/trainings/smooth-speaking/easy-starts', auth: false, name: 'Course Easy Starts' },
  { path: '/trainings/smooth-speaking/easy-starts/easy-starts-1', auth: false, name: 'Lesson Player' },
  { path: '/trainings/easier-ways', auth: false, name: 'Easier Ways' },
  { path: '/app/speak', auth: true, name: 'Speak' },
  { path: '/app/phrases', auth: true, name: 'Phrases' },
  { path: '/app/progress', auth: true, name: 'Progress' },
  { path: '/app/settings', auth: true, name: 'Settings' },
  { path: '/app/onboarding', auth: true, name: 'Onboarding' },
  { path: '/app/enroll', auth: true, name: 'Enroll' },
]

async function inspectPageLayout(page, routeName, vp) {
  return await page.evaluate(({ routeName, vp }) => {
    const issues = []
    const docWidth = document.documentElement.clientWidth
    const scrollWidth = document.documentElement.scrollWidth
    const bodyScrollWidth = document.body.scrollWidth

    if (scrollWidth > docWidth + 1) {
      issues.push(`Document horizontal overflow: scrollWidth (${scrollWidth}px) > clientWidth (${docWidth}px)`)
    }
    if (bodyScrollWidth > docWidth + 1) {
      issues.push(`Body horizontal overflow: bodyScrollWidth (${bodyScrollWidth}px) > clientWidth (${docWidth}px)`)
    }

    // Check all elements for overflow or protruding bounds
    const all = Array.from(document.querySelectorAll('*'))
    const overflowingElements = []
    for (const el of all) {
      // Ignore svgs or hidden elements
      if (el.offsetParent === null && el.tagName !== 'BODY') continue
      
      // Skip elements legitimately inside a horizontally scrollable container (e.g. .chips)
      let parent = el.parentElement
      let insideHorizontalScroll = false
      while (parent && parent !== document.body && parent !== document.documentElement) {
        const style = window.getComputedStyle(parent)
        if (style.overflowX === 'auto' || style.overflowX === 'scroll' || style.overflowX === 'hidden') {
          insideHorizontalScroll = true
          break
        }
        parent = parent.parentElement
      }
      if (insideHorizontalScroll) continue

      const rect = el.getBoundingClientRect()
      if (rect.width > 0 && rect.right > docWidth + 1.5) {
        // Tag selector
        const tag = el.tagName.toLowerCase()
        const cls = el.className ? `.${el.className.toString().split(' ').join('.')}` : ''
        const id = el.id ? `#${el.id}` : ''
        overflowingElements.push(`${tag}${id}${cls} (right: ${Math.round(rect.right)}px, width: ${Math.round(rect.width)}px)`)
      }
    }

    if (overflowingElements.length > 0) {
      issues.push(`Protruding elements (${overflowingElements.length}): ${overflowingElements.slice(0, 5).join('; ')}`)
    }

    // Check fixed footer occlusion
    // 1. In Lesson Player: verify step controls are not occluded by player footer at current scroll
    const playerFooter = document.querySelector('.lesson-player-footer')
    if (playerFooter) {
      const pfRect = playerFooter.getBoundingClientRect()
      if (pfRect.height > 0 && pfRect.top < window.innerHeight) {
        const stepButtons = Array.from(document.querySelectorAll('.lesson-player-step button, .step-content button, .checking-feedback-box button'))
        for (const btn of stepButtons) {
          const bRect = btn.getBoundingClientRect()
          if (bRect.height > 0 && bRect.bottom > pfRect.top && bRect.top < pfRect.bottom) {
            issues.push(`Lesson player step button occluded by footer: ${btn.textContent?.trim().slice(0, 30) || btn.className}`)
          }
        }
      }
    }

    // 2. On scrollable pages with fixed tabs: scroll to the bottom and verify the last interactive element is clear
    const tabs = document.querySelector('.tabs')
    if (tabs) {
      window.scrollTo(0, document.documentElement.scrollHeight)
      const tRect = tabs.getBoundingClientRect()
      if (tRect.height > 0 && tRect.top < window.innerHeight) {
        const allInteractive = Array.from(document.querySelectorAll('main button, main a[href], main input, .trainings-content button, .trainings-content a[href]'))
        if (allInteractive.length > 0) {
          const lastEl = allInteractive[allInteractive.length - 1]
          const lRect = lastEl.getBoundingClientRect()
          if (lRect.height > 0 && lRect.bottom > tRect.top && lRect.top < tRect.bottom) {
            issues.push(`Last interactive element occluded by tabs when scrolled to bottom: ${lastEl.textContent?.trim().slice(0, 30) || lastEl.className}`)
          }
        }
      }
      // restore scroll
      window.scrollTo(0, 0)
    }

    return {
      docWidth,
      scrollWidth,
      bodyScrollWidth,
      issues,
    }
  }, { routeName, vp })
}

async function run() {
  console.log('Starting comprehensive responsive audit across 16 viewports and 14 routes...')
  const browser = await chromium.launch({
    headless: true,
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
  })

  const results = []
  let totalIssues = 0

  for (const vp of VIEWPORTS) {
    console.log(`\nTesting Viewport ${vp.id}: ${vp.name} (${vp.width}x${vp.height})`)
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      deviceScaleFactor: 1,
    })

    const page = await context.newPage()

    // Sign in first so cookies / token are stored in this context
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' })
    await page.fill('input[type=email]', 'demo@sunn.app')
    await page.fill('input[type=password]', 'password123')
    await page.click('button[type=submit]')
    await page.waitForURL('**/app/**', { timeout: 8000 }).catch(() => {})
    await page.waitForTimeout(400)

    // Set onboarded in localStorage
    await page.evaluate(() => {
      for (let i = 1; i <= 50; i++) {
        localStorage.setItem(`sunn.onboarded.${i}`, 'true')
      }
    })

    for (const r of ROUTES) {
      await page.goto(`${BASE_URL}${r.path}`, { waitUntil: 'networkidle' })
      await page.waitForTimeout(400)
      const audit = await inspectPageLayout(page, r.name, vp)

      if (audit.issues.length > 0) {
        console.log(`  ❌ [${r.name}] Issues:`)
        for (const iss of audit.issues) {
          console.log(`     - ${iss}`)
          totalIssues++
        }
        results.push({ vp: vp.id, route: r.path, issues: audit.issues })
      } else {
        // passed
      }
    }

    await context.close()
  }

  await browser.close()

  console.log(`\nAudit complete! Total issues detected: ${totalIssues}`)
  if (totalIssues > 0) {
    console.log('\nSummary of detected layout/responsive issues:')
    for (const res of results) {
      console.log(`[${res.vp} - ${res.route}]: ${res.issues.join(' | ')}`)
    }
  } else {
    console.log('✅ ALL 16 VIEWPORTS AND 14 ROUTES PASSED ZERO HORIZONTAL OVERFLOW AND OCCLUSION CHECKS!')
  }
}

run().catch((err) => {
  console.error(err)
  process.exit(1)
})
