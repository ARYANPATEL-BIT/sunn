import { expect, markOnboarded, signUp, t, test } from './helpers.js'

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

  // Restart returns to Step 1
  await bar.getByRole('button', { name: t('en', 'presenter.restart') }).click()
  await expect(page).toHaveURL(/\/app\/onboarding$/)
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 1, total: 5 }))).toBeVisible()

  // Close and reopen with Alt+P
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

test('direct step pill navigation and previous button backwards flow', async ({ page }) => {
  const user = await signUp(page.request)
  await markOnboarded(page, user)
  await page.goto('/app/onboarding')

  await page.getByRole('button', { name: t('en', 'presenter.enter') }).click()
  const bar = page.getByRole('region', { name: t('en', 'presenter.title') })
  await expect(bar).toBeVisible()

  // Directly click Step 4 (Settings) pill if wide stepper is present
  const wideStepper = bar.locator('.wide-stepper')
  if (await wideStepper.isVisible()) {
    const step4Btn = wideStepper.getByRole('button', { name: /4|Settings/i })
    await step4Btn.click()
    await expect(page).toHaveURL(/\/app\/settings$/)
    await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 4, total: 5 }))).toBeVisible()

    // Step backwards using Previous button
    await bar.getByRole('button', { name: t('en', 'presenter.prev') }).click()
    await expect(page).toHaveURL(/\/app\/speak$/)
    await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 3, total: 5 }))).toBeVisible()
  }
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
