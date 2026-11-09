import {
  expect, expectNoLeaks, LANGS, markOnboarded, openSpeak, signUp, t, test,
} from './helpers.js'

for (const lang of LANGS) {
  test.describe(`trainings browsing, ${lang}`, () => {
    test.use({ lang })

    test('open from landing nav, browse category and course, honest note', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      // 1. Open trainings from landing page navigation (on desktop) or navigate to trainings
      await page.goto('/')
      const navLink = page.getByRole('banner').getByRole('link', { name: t(lang, 'nav.trainings') })
      if (await navLink.isVisible()) {
        await navLink.click()
      } else {
        await page.goto('/trainings')
      }

      await expect(page).toHaveURL(/\/trainings$/)
      await expect(
        page.getByRole('heading', { level: 1, name: t(lang, 'trainings.homeTitle') }),
      ).toBeVisible()

      // Verify the honest note is present on trainings home
      const honestNote = page.locator('.trainings-honest-note')
      await expect(honestNote).toBeVisible()
      await expect(honestNote).toContainText(t(lang, 'trainings.honestNote'))

      // 2. Open a category (smooth-speaking)
      const smoothCategory = page.locator('.category-card[href="/trainings/smooth-speaking"]')
      await expect(smoothCategory).toBeVisible()
      await smoothCategory.click()

      await expect(page).toHaveURL(/\/trainings\/smooth-speaking$/)
      await expect(page.locator('.category-page-title')).toBeVisible()
      await expect(page.locator('.category-page-description')).toBeVisible()
      await expect(page.locator('.trainings-honest-note')).toBeVisible()

      // 3. Open a course (easy-starts)
      const easyStartsLink = page.locator('.course-card-link[href="/trainings/smooth-speaking/easy-starts"]')
      await expect(easyStartsLink).toBeVisible()
      await easyStartsLink.click()

      await expect(page).toHaveURL(/\/trainings\/smooth-speaking\/easy-starts$/)
      await expect(page.locator('.course-page-title')).toBeVisible()

      // Verify lessons list and honest note on course page
      const lessonsList = page.locator('.lessons-list .lesson-row')
      await expect(lessonsList).toHaveCount(4)
      await expect(page.locator('.trainings-honest-note')).toBeVisible()

      // 4. Browsing logged out: clicking practise button redirects to login
      const startBtn = page.locator('.course-primary-btn')
      await expect(startBtn).toBeVisible()
      await startBtn.click()

      await expect(page).toHaveURL(/\/login\?next=/)
    })

    test('open trainings from bottom tab bar when signed in', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      await page.goto('/app/speak')
      const trainingsTab = page.locator('.tabs').getByRole('link', { name: t(lang, 'tab.trainings') })
      await expect(trainingsTab).toBeVisible()
      await trainingsTab.click()

      await expect(page).toHaveURL(/\/trainings$/)
      await expect(
        page.getByRole('heading', { level: 1, name: t(lang, 'trainings.homeTitle') }),
      ).toBeVisible()
      await expect(page.locator('.category-card')).toHaveCount(4)
      await expect(page.locator('.trainings-honest-note')).toBeVisible()
    })
  })
}
