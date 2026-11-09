import {
  expect, expectNoLeaks, markOnboarded, openSpeak, signUp, t, test,
} from './helpers.js'

async function assertLayoutHealth(page, screenName) {
  const layout = await page.evaluate(() => {
    const docW = document.documentElement.clientWidth
    const scrollW = document.documentElement.scrollWidth
    const bodyW = document.body.scrollWidth
    return {
      docW,
      scrollW,
      bodyW,
      overflow: scrollW > docW + 1 || bodyW > docW + 1,
    }
  })
  expect(
    layout.overflow,
    `Horizontal layout overflow on ${screenName}: scrollWidth=${layout.scrollW}px, bodyWidth=${layout.bodyW}px, clientWidth=${layout.docW}px`,
  ).toBe(false)
}

test.describe('Responsive Layout Health and Public Routes', () => {
  const VIEWPORTS = [
    { name: 'Ultra-Compact Mobile', width: 320, height: 568 },
    { name: 'Standard Android', width: 360, height: 800 },
    { name: 'Standard iPhone', width: 390, height: 844 },
    { name: 'Landscape Mobile', width: 844, height: 390 },
    { name: 'Tablet Portrait', width: 768, height: 1024 },
    { name: 'Desktop Large', width: 1440, height: 900 },
  ]

  for (const vp of VIEWPORTS) {
    test(`Landing page layout health on ${vp.name} (${vp.width}x${vp.height})`, async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')
      await page.setViewportSize({ width: vp.width, height: vp.height })
      await page.goto('/')
      await page.waitForLoadState('networkidle')

      await assertLayoutHealth(page, `Landing (${vp.name})`)
      await expect(page.locator('.landing').first()).toBeVisible()

      if (vp.width < 1024) {
        // Verify mobile navigation toggle and drawer
        const toggle = page.locator('.mobile-nav-toggle')
        await expect(toggle).toBeVisible()
        await toggle.click()

        const drawer = page.locator('.mobile-nav-drawer')
        await expect(drawer).toBeVisible()
        await assertLayoutHealth(page, `Landing Drawer Open (${vp.name})`)

        // Close drawer with Escape
        await page.keyboard.press('Escape')
        await expect(drawer).toBeHidden()
      } else {
        // Desktop nav links visible
        await expect(page.locator('.nav-links')).toBeVisible()
      }
    })
  }

  test('Public auth and trainings catalog routes on compact mobile (320x568)', async ({ page, watch }) => {
    watch.allow(401, '/api/auth/me')
    await page.setViewportSize({ width: 320, height: 568 })

    // 1. Sign In route
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Login (320x568)')
    await expect(page.locator('input[type=email]')).toBeVisible()
    await expect(page.locator('input[type=password]')).toBeVisible()

    // 2. Sign Up route
    await page.goto('/signup')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Signup (320x568)')
    await expect(page.locator('input[type=email]')).toBeVisible()

    // 3. Trainings catalog home
    await page.goto('/trainings')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Trainings Catalog (320x568)')
    await expect(page.locator('.category-card').first()).toBeVisible()
    await expect(page.locator('.trainings-honest-note')).toBeVisible()

    // 4. Category page
    await page.goto('/trainings/smooth-speaking')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Category Smooth Speaking (320x568)')
    await expect(page.locator('.course-card').first()).toBeVisible()

    // 5. Course page
    await page.goto('/trainings/smooth-speaking/easy-starts')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Course Easy Starts (320x568)')
    await expect(page.locator('.lesson-row').first()).toBeVisible()

    // 6. Lesson player
    await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Lesson Player (320x568)')
    await expect(page.locator('.lesson-player-page')).toBeVisible()
    await expect(page.locator('.lesson-player-header')).toBeVisible()
    await expect(page.locator('.lesson-player-footer')).toBeVisible()

    // 7. Easier ways tool
    await page.goto('/trainings/easier-ways')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Easier Ways (320x568)')
    await expect(page.locator('.easier-ways-input')).toBeVisible()
  })
})

test.describe('Authenticated Application Responsive Features', () => {
  test('Bottom tabs and app screens on mobile (360x800) and landscape (844x390)', async ({ page }) => {
    const user = await signUp(page.request)
    await markOnboarded(page, user)

    // Test on portrait mobile 360x800
    await page.setViewportSize({ width: 360, height: 800 })
    await openSpeak(page.request, user)
    await page.goto('/app/speak')
    await page.waitForLoadState('networkidle')

    // Speak screen
    await assertLayoutHealth(page, 'Speak Screen (360x800)')
    const tabs = page.locator('.tabs')
    await expect(tabs).toBeVisible()
    await expect(page.locator('.tab')).toHaveCount(6)

    // Phrases screen
    await page.goto('/app/phrases')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Phrases Screen (360x800)')

    // Progress screen
    await page.goto('/app/progress')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Progress Screen (360x800)')
    await expect(page.locator('.days-practised-grid')).toBeVisible()

    // Settings screen
    await page.goto('/app/settings')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Settings Screen (360x800)')

    // Switch to Landscape Mobile 844x390
    await page.setViewportSize({ width: 844, height: 390 })
    await page.goto('/app/speak')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Speak Screen Landscape (844x390)')
    await expect(page.locator('.tabs')).toBeVisible()

    // Lesson player in landscape: verify step buttons are clear of footer
    await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Lesson Player Landscape (844x390)')

    const clearance = await page.evaluate(() => {
      const footer = document.querySelector('.lesson-player-footer')
      const nextBtn = document.querySelector('.player-next-btn')
      if (!footer || !nextBtn) return { valid: false }
      const fRect = footer.getBoundingClientRect()
      const bRect = nextBtn.getBoundingClientRect()
      return {
        valid: true,
        buttonVisible: bRect.width > 0 && bRect.height > 0,
        buttonInsideFooter: bRect.top >= fRect.top && bRect.bottom <= fRect.bottom,
      }
    })
    expect(clearance.valid).toBe(true)
    expect(clearance.buttonVisible).toBe(true)
    expect(clearance.buttonInsideFooter).toBe(true)
  })

  test('Modal dialogs fit within viewport and support keyboard dismissal across devices', async ({ page }) => {
    const user = await signUp(page.request)
    await markOnboarded(page, user)

    const VIEWPORTS = [
      { name: 'Mobile', width: 360, height: 800 },
      { name: 'Landscape', width: 844, height: 390 },
      { name: 'Desktop', width: 1440, height: 900 },
    ]

    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height })
      await page.goto('/app/phrases')
      await page.waitForLoadState('networkidle')

      // Open Add Phrase modal sheet
      const addBtn = page.getByRole('button', { name: t('en', 'phrases.add') })
      await expect(addBtn).toBeVisible()
      await addBtn.click()

      const dialog = page.locator('dialog.sheet')
      await expect(dialog).toBeVisible()

      // Assert sheet fits cleanly inside viewport
      const bounds = await dialog.evaluate((el) => {
        const rect = el.getBoundingClientRect()
        return {
          width: rect.width,
          height: rect.height,
          right: rect.right,
          bottom: rect.bottom,
          winWidth: window.innerWidth,
          winHeight: window.innerHeight,
        }
      })
      expect(bounds.width).toBeLessThanOrEqual(bounds.winWidth + 1)
      expect(bounds.height).toBeLessThanOrEqual(bounds.winHeight + 1)

      // Test Escape dismisses modal
      await page.keyboard.press('Escape')
      await expect(dialog).toBeHidden()
    }
  })

  test('Onboarding and Enroll flows maintain valid responsive sizing', async ({ page }) => {
    const user = await signUp(page.request)

    // Onboarding at 320x568
    await page.setViewportSize({ width: 320, height: 568 })
    await page.goto('/app/onboarding')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Onboarding (320x568)')

    // Enroll at 320x568
    await page.goto('/app/enroll')
    await page.waitForLoadState('networkidle')
    await assertLayoutHealth(page, 'Enroll (320x568)')
  })
})
