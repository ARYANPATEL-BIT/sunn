import { expect, markOnboarded, signUp, t, test } from './helpers.js'

test.describe('Auth, Protected Routes, Navigation & Global UI Fixes', () => {
  test('logged-in user is redirected away from public landing, login, and signup pages', async ({ page }) => {
    const user = await signUp(page.request)
    await markOnboarded(page, user)
    await page.goto('/app/speak')
    await expect(page).toHaveURL(/\/app\/speak$/)

    // Direct navigation to landing page redirects to /app/speak
    await page.goto('/')
    await expect(page).toHaveURL(/\/app\/speak$/)

    // Direct navigation to /login redirects to /app/speak
    await page.goto('/login')
    await expect(page).toHaveURL(/\/app\/speak$/)

    // Direct navigation to /signup redirects to /app/speak
    await page.goto('/signup')
    await expect(page).toHaveURL(/\/app\/speak$/)
  })

  test('public landing page navigation, active states, and direct section URLs', async ({ page, watch }) => {
    watch.allow(401, '/api/auth/me')

    // 1. Visit landing page while logged out
    await page.goto('/')
    await expect(page).toHaveURL(/\/$/)

    // Verify Sign in button is visible for logged-out visitors
    const signInBtn = page.locator('.site-nav .bar-end .nav-link')
    await expect(signInBtn).toBeVisible()
    await expect(signInBtn).toHaveText(t('en', 'nav.signIn'))
    await expect(signInBtn).toHaveAttribute('href', '/login')

    // 2. Test navigation links (handling both desktop and mobile drawer)
    const isDesktopNav = await page.locator('.site-nav .nav-links').isVisible()
    if (isDesktopNav) {
      // Click Privacy link in nav
      const privacyLink = page.locator('.site-nav .nav-links a[href="#privacy"]')
      await privacyLink.click()
      await expect(privacyLink).toHaveClass(/active/)
      await expect(page.locator('#privacy')).toBeInViewport()

      // Click Questions (FAQ) link in nav
      const faqLink = page.locator('.site-nav .nav-links a[href="#faq"]')
      await faqLink.click()
      await expect(faqLink).toHaveClass(/active/)
      await expect(page.locator('#faq')).toBeInViewport()

      // Click How It Works link in nav
      const howLink = page.locator('.site-nav .nav-links a[href="#how"]')
      await howLink.click()
      await expect(howLink).toHaveClass(/active/)
      await expect(page.locator('#how')).toBeInViewport()
    } else {
      // Mobile drawer navigation
      const menuBtn = page.locator('.mobile-nav-toggle')
      await menuBtn.click()
      await expect(page.locator('#landing-mobile-menu')).toBeVisible()

      const mobilePrivacyLink = page.locator('.mobile-nav-list a[href="#privacy"]')
      await mobilePrivacyLink.click()
      await expect(page.locator('#privacy')).toBeInViewport()
    }

    // 3. Direct section route URLs
    await page.goto('/privacy')
    await expect(page.locator('#privacy')).toBeInViewport()

    await page.goto('/faq')
    await expect(page.locator('#faq')).toBeInViewport()
  })

  test('header theme toggle switches strictly between light and dark with sun and moon icons', async ({ page }) => {
    const user = await signUp(page.request)
    await markOnboarded(page, user)
    await page.goto('/app/speak')

    const themeBtn = page.locator('.app-header .theme-toggle')
    await expect(themeBtn).toBeVisible()

    // Set initial light theme
    await page.evaluate(() => {
      localStorage.setItem('sunn.theme', 'light')
      document.documentElement.dataset.theme = 'light'
    })
    await page.reload()

    // In light theme: icon is sun
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
    await expect(themeBtn.locator('svg')).toHaveClass(/icon/)

    // Clicking switches immediately to dark theme
    await themeBtn.click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    const savedAfterClick = await page.evaluate(() => localStorage.getItem('sunn.theme'))
    expect(savedAfterClick).toBe('dark')

    // Clicking again switches immediately back to light theme (no 3rd automatic state in header)
    await themeBtn.click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
    const savedAfterSecondClick = await page.evaluate(() => localStorage.getItem('sunn.theme'))
    expect(savedAfterSecondClick).toBe('light')

    // Verify Settings still retains all three options: light, dark, system
    await page.goto('/app/settings')
    await expect(page.getByRole('radio', { name: t('en', 'theme.light') })).toBeVisible()
    await expect(page.getByRole('radio', { name: t('en', 'theme.dark') })).toBeVisible()
    await expect(page.getByRole('radio', { name: t('en', 'theme.system') })).toBeVisible()
  })

  test('presenter demo mode always initializes at Step 1 from any starting route', async ({ page }) => {
    const user = await signUp(page.request)
    await markOnboarded(page, user)

    // Test Case A: Launch from /app/speak
    await page.goto('/app/speak')
    await expect(page).toHaveURL(/\/app\/speak$/)
    await page.getByRole('button', { name: t('en', 'presenter.enter') }).click()

    let bar = page.getByRole('region', { name: t('en', 'presenter.title') })
    await expect(bar).toBeVisible()
    await expect(page).toHaveURL(/\/app\/onboarding$/)
    await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 1, total: 5 }))).toBeVisible()

    // Close demo
    await bar.getByRole('button', { name: t('en', 'presenter.exit') }).click()
    await expect(bar).toHaveCount(0)

    // Test Case B: Launch from /app/phrases
    await page.goto('/app/phrases')
    await expect(page).toHaveURL(/\/app\/phrases$/)
    await page.getByRole('button', { name: t('en', 'presenter.enter') }).click()

    bar = page.getByRole('region', { name: t('en', 'presenter.title') })
    await expect(bar).toBeVisible()
    await expect(page).toHaveURL(/\/app\/onboarding$/)
    await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 1, total: 5 }))).toBeVisible()

    // Close demo
    await bar.getByRole('button', { name: t('en', 'presenter.exit') }).click()
    await expect(bar).toHaveCount(0)

    // Test Case C: Launch via keyboard shortcut Alt+P from /app/progress
    await page.goto('/app/progress')
    await expect(page).toHaveURL(/\/app\/progress$/)
    await page.locator('body').click()
    await page.keyboard.press('Alt+P')

    bar = page.getByRole('region', { name: t('en', 'presenter.title') })
    await expect(bar).toBeVisible()
    await expect(page).toHaveURL(/\/app\/onboarding$/)
    await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 1, total: 5 }))).toBeVisible()
  })

  test('logout navigates to landing page and subsequent protected route navigation redirects to login', async ({ page, watch }) => {
    watch.allow(401, '/api/auth/me')
    const user = await signUp(page.request)
    await markOnboarded(page, user)
    await page.goto('/app/settings')

    // Log out (works on both mobile settings screen and desktop header)
    const logoutBtn = page.getByRole('button', { name: t('en', 'app.logOut') }).first()
    await logoutBtn.click()
    await expect(page).toHaveURL(/\/$/)

    // Verify public landing page is now accessible
    await expect(page.locator('.site-nav')).toBeVisible()

    // Attempting to navigate back to /app/speak redirects to /login?next=...
    await page.goto('/app/speak')
    await expect(page).toHaveURL(/\/login\?next=%2Fapp%2Fspeak$/)

    // Attempting to navigate to /app/settings redirects to /login?next=...
    await page.goto('/app/settings')
    await expect(page).toHaveURL(/\/login\?next=%2Fapp%2Fsettings$/)
  })
})
