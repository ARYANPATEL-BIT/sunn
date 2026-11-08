import {
  expect, expectNoLeaks, LANGS, markOnboarded, openSpeak, signUp, t, test,
} from './helpers.js'

for (const lang of LANGS) {
  test.describe(`tricky sounds & easier alternatives, ${lang}`, () => {
    test.use({ lang })

    test('tricky sounds card with data and empty state on trainings home', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      // 1. Logged in on /trainings shows tricky sounds and easier ways cards
      await page.goto('/trainings')
      await expect(page.locator('.tricky-sounds-card')).toBeVisible()
      await expect(page.locator('.easier-ways-card')).toBeVisible()

      // Tricky sounds with data from mock backend
      const soundRows = page.locator('.tricky-sound-row')
      await expect(soundRows.first()).toBeVisible()
      const soundCount = await soundRows.count()
      expect(soundCount).toBeGreaterThanOrEqual(1)
      expect(soundCount).toBeLessThanOrEqual(3)

      // Practise button navigates to the practice lesson
      const firstPractiseBtn = soundRows.first().locator('.practise-sound-btn')
      if (await firstPractiseBtn.isVisible()) {
        await firstPractiseBtn.click()
        await expect(page).toHaveURL(/\/trainings\/(clear-sounds|clear-speech)\/s-and-sh\/s-and-sh-1/)
      }

      // 2. Empty state when tricky-sounds returns []
      await page.route('**/me/trainings/tricky-sounds', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        })
      })

      await page.goto('/trainings')
      await expect(page.locator('.tricky-sounds-card')).toBeVisible()
      await expect(page.locator('.personalized-empty-text')).toContainText(
        t(lang, 'trainings.trickySoundsEmpty'),
      )
    })

    test('easier ways tool search, alternatives cards, practice, and add to phrases', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      // 1. Navigate to easier ways from the card on /trainings
      await page.goto('/trainings')
      const openToolBtn = page.locator('.open-easier-ways-btn')
      await expect(openToolBtn).toBeVisible()
      await openToolBtn.click()

      await expect(page).toHaveURL(/\/trainings\/easier-ways$/)
      await expect(page.locator('.trainings-title')).toContainText(t(lang, 'easierWays.title'))

      // Example is visible when no search has been performed
      await expect(page.locator('.easier-ways-example-box')).toBeVisible()

      // 2. Search for a phrase
      const searchInput = page.locator('#easier-ways-input')
      await searchInput.fill(lang === 'hi' ? 'शुक्रिया' : 'Thank you')

      const searchBtn = page.locator('.easier-ways-search-btn')
      await searchBtn.click()

      // 3. Alternative cards rendered
      const altCards = page.locator('.alternative-card')
      await expect(altCards.first()).toBeVisible({ timeout: 5000 })
      const altsCount = await altCards.count()
      expect(altsCount).toBeGreaterThanOrEqual(1)
      expect(altsCount).toBeLessThanOrEqual(4)

      // Verify card elements: source badge, phrase text, avoids line
      await expect(altCards.first().locator('.alt-source-pill')).toBeVisible()
      await expect(altCards.first().locator('.alt-phrase-text')).toBeVisible()
      await expect(altCards.first().locator('.alt-avoids-line')).toBeVisible()

      // 4. In-place practice (SpeakWithMeStep in paced mode)
      const practiseBtn = altCards.first().getByRole('button', { name: t(lang, 'easierWays.practiseAction') })
      await practiseBtn.click()

      const practiceModal = page.locator('.easier-ways-practice-modal')
      await expect(practiceModal).toBeVisible()
      await expect(practiceModal.locator('.step-speak-with-me')).toBeVisible()
      await expect(practiceModal.locator('.pace-range-input')).toBeVisible()

      // Close practice
      const closePracticeBtn = practiceModal.getByRole('button', { name: t(lang, 'easierWays.closePractice') })
      await closePracticeBtn.click()
      await expect(practiceModal).toHaveCount(0)

      // 5. Add alternative to my phrases
      const addBtn = altCards.first().getByRole('button', { name: t(lang, 'easierWays.addPhraseAction') })
      await addBtn.click()

      await expect(altCards.first().locator('.alt-added-notice')).toBeVisible()
      await expect(altCards.first().locator('.added-msg')).toContainText(t(lang, 'easierWays.addedSuccess'))
    })

    test('open easier ways from phrases screen with pre-filled text', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      // Navigate to /app/phrases
      await page.goto('/app/phrases')
      await expect(page.locator('.phrase-card').first()).toBeVisible()

      // Click "Easier ways" text button on the first phrase card
      const easierWaysBtn = page.locator('.phrase-easier-ways-btn').first()
      await expect(easierWaysBtn).toBeVisible()
      await easierWaysBtn.click()

      // Verifies navigation to /trainings/easier-ways with query/state pre-filled and searched
      await expect(page).toHaveURL(/\/trainings\/easier-ways$/)
      const searchInput = page.locator('#easier-ways-input')
      await expect(searchInput).not.toHaveValue('')
      await expect(page.locator('.alternative-card').first()).toBeVisible({ timeout: 5000 })
    })

    test('trainings section on progress tab shows metrics, 7 day squares, and courses', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      await page.goto('/app/progress')
      const trainingsSection = page.locator('.trainings-progress-section')
      await expect(trainingsSection).toBeVisible()

      // Heading and description
      await expect(trainingsSection.locator('h2')).toContainText(t(lang, 'progress.trainingsHeading'))

      // Lessons done and minutes metrics
      await expect(trainingsSection.getByText(t(lang, 'progress.lessonsDone'))).toBeVisible()
      await expect(trainingsSection.getByText(t(lang, 'progress.minutesPractised'))).toBeVisible()

      // 7 day square elements (not dots)
      const dayBoxes = trainingsSection.locator('.day-square-box')
      await expect(dayBoxes).toHaveCount(7)

      // Backend progress mock returns days_this_week: 2, so 2 days should have the check icon
      const completedDays = trainingsSection.locator('.day-square-box.done')
      await expect(completedDays).toHaveCount(2)
      await expect(completedDays.first().locator('.day-check-icon')).toBeVisible()

      // Courses in progress list
      const courseCard = trainingsSection.locator('.course-progress-card').first()
      await expect(courseCard).toBeVisible()
      await expect(courseCard.locator('.meter')).toBeVisible()
      const continueCourseBtn = courseCard.locator('button')
      await expect(continueCourseBtn).toBeVisible()
      await continueCourseBtn.click()
      await expect(page).toHaveURL(/\/trainings\/smooth-speaking\/easy-starts/)
    })
  })
}
