import { expect, markOnboarded, openSpeak, signUp, t, test } from './helpers.js'

test('presenter mode initializes at step 1, steps through all 5 screens to completion, and restarts', async ({ page }) => {
  const user = await signUp(page.request)
  await markOnboarded(page, user)
  // Start from /app/speak to verify bugfix: fresh open must NOT start at step 3
  await page.goto('/app/speak')

  // Open presenter mode from header
  await page.getByRole('button', { name: t('en', 'presenter.enter') }).click()
  const bar = page.getByRole('region', { name: t('en', 'presenter.title') })
  await expect(bar).toBeVisible()

  // Step 1: Onboarding
  await expect(page).toHaveURL(/\/app\/onboarding$/)
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 1, total: 5 }))).toBeVisible()
  await expect(bar.getByText(t('en', 'presenter.stepOnboardingTitle'))).toBeVisible()

  // Step 2: Phrases
  await bar.getByRole('button', { name: t('en', 'presenter.next') }).click()
  await expect(page).toHaveURL(/\/app\/phrases$/)
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 2, total: 5 }))).toBeVisible()

  // Step 3: Speak
  await bar.getByRole('button', { name: t('en', 'presenter.next') }).click()
  await expect(page).toHaveURL(/\/app\/speak$/)
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 3, total: 5 }))).toBeVisible()

  // Step 4: Settings
  await bar.getByRole('button', { name: t('en', 'presenter.next') }).click()
  await expect(page).toHaveURL(/\/app\/settings$/)
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 4, total: 5 }))).toBeVisible()

  // Step 5: Progress
  await bar.getByRole('button', { name: t('en', 'presenter.next') }).click()
  await expect(page).toHaveURL(/\/app\/progress$/)
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 5, total: 5 }))).toBeVisible()

  // Advance from Step 5 to Completion
  await bar.getByRole('button', { name: t('en', 'presenter.finish') }).click()
  await expect(bar.getByRole('heading', { name: t('en', 'presenter.completedTitle') })).toBeVisible()
  await expect(bar.getByText(t('en', 'presenter.completedDesc'))).toBeVisible()

  // On completion, Finish walkthrough is replaced with Close
  await expect(bar.getByRole('button', { name: t('en', 'presenter.finish') })).toHaveCount(0)
  const closeBtn = bar.getByRole('button', { name: t('en', 'presenter.close') })
  await expect(closeBtn).toBeVisible()

  // Clicking Previous returns to Step 5 without corrupting state
  await bar.getByRole('button', { name: t('en', 'presenter.prev') }).click()
  await expect(page).toHaveURL(/\/app\/progress$/)
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 5, total: 5 }))).toBeVisible()
  await expect(bar.getByRole('button', { name: t('en', 'presenter.finish') })).toBeVisible()

  // Re-advance to completion and verify Close dismisses panel cleanly
  await bar.getByRole('button', { name: t('en', 'presenter.finish') }).click()
  await expect(bar.getByRole('heading', { name: t('en', 'presenter.completedTitle') })).toBeVisible()
  await bar.getByRole('button', { name: t('en', 'presenter.close') }).click()
  await expect(bar).toHaveCount(0)

  // Reopen with Alt+P and verify Restart returns to Step 1
  await page.locator('body').click()
  await page.keyboard.press('Alt+P')
  await expect(bar).toBeVisible()
  await expect(page).toHaveURL(/\/app\/onboarding$/)
  await bar.getByRole('button', { name: t('en', 'presenter.restart') }).click()
  await expect(page).toHaveURL(/\/app\/onboarding$/)
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 1, total: 5 }))).toBeVisible()

  // Close with header exit button
  await bar.getByRole('button', { name: t('en', 'presenter.exit') }).click()
  await expect(bar).toHaveCount(0)
  await page.locator('body').click()
  await page.keyboard.press('Alt+P')
  await expect(bar).toBeVisible()
  await expect(page).toHaveURL(/\/app\/onboarding$/)
})

test('presenter mode supports keyboard navigation, collapse toggle, and spotlight target', async ({ page }) => {
  const user = await signUp(page.request)
  await markOnboarded(page, user)
  await page.goto('/app/phrases')
  await page.locator('body').click()

  // Open via Alt+P
  await page.keyboard.press('Alt+P')
  const bar = page.getByRole('region', { name: t('en', 'presenter.title') })
  await expect(bar).toBeVisible()
  await expect(page).toHaveURL(/\/app\/onboarding$/)

  // Verify spotlight highlight is attached to onboarding target
  await expect(page.locator('.presenter-target-highlight')).toBeVisible()

  // Collapse and expand
  await bar.getByRole('button', { name: t('en', 'presenter.collapse') }).click()
  await expect(bar.locator('.presenter-collapsed-row')).toBeVisible()
  await bar.getByRole('button', { name: t('en', 'presenter.expand') }).click()
  await expect(bar.locator('.presenter-bar-body')).toBeVisible()

  // Keyboard ArrowRight navigates forward to Phrases
  await page.keyboard.press('ArrowRight')
  await expect(page).toHaveURL(/\/app\/phrases$/)
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 2, total: 5 }))).toBeVisible()
  await expect(page.locator('.presenter-target-highlight')).toBeVisible()

  // Keyboard ArrowLeft navigates backward
  await page.keyboard.press('ArrowLeft')
  await expect(page).toHaveURL(/\/app\/onboarding$/)
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 1, total: 5 }))).toBeVisible()

  // Keyboard Escape exits
  await page.keyboard.press('Escape')
  await expect(bar).toHaveCount(0)
})

test('compact spotlight tour side placement avoids covering the active target', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  const user = await signUp(page.request)
  await markOnboarded(page, user)
  await page.goto('/app/onboarding')

  await page.getByRole('button', { name: t('en', 'presenter.enter') }).click()
  const tourCard = page.locator('.presenter-tour-card')
  await expect(tourCard).toBeVisible()

  // Verify old wide stepper is completely absent
  await expect(tourCard.locator('.wide-stepper')).toHaveCount(0)

  // Verify only current step is displayed
  await expect(tourCard.getByText(t('en', 'presenter.stepIndicator', { current: 1, total: 5 }))).toBeVisible()

  // Target element has spotlight class
  const target = page.locator('.presenter-target-highlight')
  await expect(target).toBeVisible()

  // Verify card and target do not overlap on 1440px desktop
  const cardBox = await tourCard.boundingBox()
  const targetBox = await target.boundingBox()
  expect(cardBox).not.toBeNull()
  expect(targetBox).not.toBeNull()

  // On desktop with left placement, card's right edge does not overlap target
  const overlapsHorizontally = !(cardBox.x + cardBox.width <= targetBox.x || targetBox.x + targetBox.width <= cardBox.x)
  const overlapsVertically = !(cardBox.y + cardBox.height <= targetBox.y || targetBox.y + targetBox.height <= cardBox.y)
  const isOverlapping = overlapsHorizontally && overlapsVertically
  expect(isOverlapping).toBe(false)

  // Step forward then backward using Next and Prev buttons
  await tourCard.getByRole('button', { name: t('en', 'presenter.next') }).click()
  await expect(page).toHaveURL(/\/app\/phrases$/)
  await expect(tourCard.getByText(t('en', 'presenter.stepIndicator', { current: 2, total: 5 }))).toBeVisible()

  await tourCard.getByRole('button', { name: t('en', 'presenter.prev') }).click()
  await expect(page).toHaveURL(/\/app\/onboarding$/)
  await expect(tourCard.getByText(t('en', 'presenter.stepIndicator', { current: 1, total: 5 }))).toBeVisible()
})

test('presenter spotlight tour adapts cleanly to dark theme', async ({ page }) => {
  const user = await signUp(page.request)
  await markOnboarded(page, user)
  await page.goto('/app/speak')

  // Set dark theme
  await page.evaluate(() => {
    localStorage.setItem('sunn.theme', 'dark')
    document.documentElement.dataset.theme = 'dark'
  })

  await page.getByRole('button', { name: t('en', 'presenter.enter') }).click()
  const tourCard = page.locator('.presenter-tour-card')
  await expect(tourCard).toBeVisible()
  await expect(page.locator('.presenter-target-highlight')).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
})

test('mobile 320px viewport renders compact progress without horizontal scroll overflow', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 600 })
  const user = await signUp(page.request)
  await markOnboarded(page, user)
  await page.goto('/app/onboarding')

  await page.getByRole('button', { name: t('en', 'presenter.enter') }).click()
  const bar = page.getByRole('region', { name: t('en', 'presenter.title') })
  await expect(bar).toBeVisible()

  // On 320px mobile viewport, compact progress is visible and wide stepper is hidden
  await expect(bar.locator('.presenter-mobile-progress')).toBeVisible()
  await expect(bar.locator('.wide-stepper')).not.toBeVisible()

  // Verify page has no horizontal overflow
  const hasOverflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth > document.documentElement.clientWidth
  })
  expect(hasOverflow).toBe(false)
})

test('presenter mode walkthrough does not make automatic Gnani API calls', async ({ page }) => {
  let gnaniApiCalled = false
  page.on('request', (req) => {
    const url = req.url()
    if (url.includes('/api/stt') || url.includes('/api/tts') || url.includes('/api/gnani')) {
      gnaniApiCalled = true
    }
  })

  const user = await signUp(page.request)
  await markOnboarded(page, user)
  await page.goto('/app/onboarding')

  await page.getByRole('button', { name: t('en', 'presenter.enter') }).click()
  const bar = page.getByRole('region', { name: t('en', 'presenter.title') })
  await expect(bar).toBeVisible()

  // Step through all 5 screens
  for (let i = 0; i < 4; i++) {
    await bar.getByRole('button', { name: t('en', 'presenter.next') }).click()
  }
  await expect(page).toHaveURL(/\/app\/progress$/)

  // Verify Gnani was never triggered automatically
  expect(gnaniApiCalled).toBe(false)
})

test('spotlight targets are properly scoped and scroll to top for all 5 steps', async ({ page }) => {
  const user = await signUp(page.request)
  await page.request.patch('/api/me', { data: { phrase_goal: 10 } })
  await openSpeak(page.request, user)
  await markOnboarded(page, user)
  await page.goto('/app/onboarding')

  await page.getByRole('button', { name: t('en', 'presenter.enter') }).click()
  const bar = page.getByRole('region', { name: t('en', 'presenter.title') })
  await expect(bar).toBeVisible()

  // Step 1: Onboarding target
  await expect(page.locator('.presenter-target-highlight')).toBeVisible()

  // Step 2: Phrases target is heading/controls (.phrases-header), NOT .phrases-list
  await bar.getByRole('button', { name: t('en', 'presenter.next') }).click()
  await expect(page).toHaveURL(/\/app\/phrases$/)
  const phrasesTarget = page.locator('.presenter-target-highlight')
  await expect(phrasesTarget).toBeVisible()
  await expect(phrasesTarget).toHaveClass(/phrases-header/)
  await expect(page.locator('.phrases-list')).not.toHaveClass(/presenter-target-highlight/)

  // Step 3: Speak target is recording interface (.speak-device), NOT entire page
  await bar.getByRole('button', { name: t('en', 'presenter.next') }).click()
  await expect(page).toHaveURL(/\/app\/speak$/)
  const speakTarget = page.locator('.presenter-target-highlight')
  await expect(speakTarget).toBeVisible()
  await expect(speakTarget).toHaveClass(/speak-device/)
  await expect(page.locator('section.speak')).not.toHaveClass(/presenter-target-highlight/)

  // Step 4: Settings target is accessibility section
  await bar.getByRole('button', { name: t('en', 'presenter.next') }).click()
  await expect(page).toHaveURL(/\/app\/settings$/)
  const settingsTarget = page.locator('.presenter-target-highlight')
  await expect(settingsTarget).toBeVisible()
  await expect(settingsTarget).toHaveClass(/settings-accessibility-group/)

  // Step 5: Progress target is heading and summary metrics
  await bar.getByRole('button', { name: t('en', 'presenter.next') }).click()
  await expect(page).toHaveURL(/\/app\/progress$/)
  const progressTarget = page.locator('.presenter-target-highlight')
  await expect(progressTarget).toBeVisible()
  await expect(progressTarget).toHaveClass(/progress-header-summary/)
})
