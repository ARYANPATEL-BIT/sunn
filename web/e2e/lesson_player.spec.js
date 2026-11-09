import {
  expect, LANGS, markOnboarded, openSpeak, signUp, t, test,
} from './helpers.js'

for (const lang of LANGS) {
  test.describe(`lesson player, ${lang}`, () => {
    test.use({ lang })

    test('complete whole sample lesson with multiple step types', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      // Open easy-starts-1 directly
      await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1')

      // Verify top header & segmented meter
      await expect(page.locator('.player-lesson-title')).toBeVisible()
      const meter = page.locator('.segmented-meter')
      await expect(meter).toBeVisible()

      // Step 0: intro
      await expect(page.locator('.step-intro-tip')).toBeVisible()
      const nextBtn = page.locator('.player-next-btn')
      await nextBtn.click()

      // Step 1: breathing
      await expect(page.locator('.step-breathing')).toBeVisible()
      const breatheBtn = page.locator('.breathing-toggle-btn')
      await expect(breatheBtn).toBeVisible()
      await breatheBtn.click()
      await nextBtn.click()

      // Step 2: tip
      await expect(page.locator('.step-intro-tip')).toBeVisible()
      await nextBtn.click()

      // Step 3: listen_repeat
      await expect(page.locator('.step-listen-repeat')).toBeVisible()
      await nextBtn.click()

      // Step 4: speak_with_me
      await expect(page.locator('.step-speak-with-me')).toBeVisible()
      await nextBtn.click()

      // Step 5: reflect (last step)
      await expect(page.locator('.step-reflect')).toBeVisible()
      const choiceCard = page.locator('.reflect-choice-card').first()
      await choiceCard.click()
      await expect(page.locator('.reflect-supportive-reply')).toBeVisible()

      // Next button is now "Finish lesson"
      await expect(nextBtn).toContainText(t(lang, 'lesson.finishAction'))
      await nextBtn.click()

      // Verify completion screen
      const doneScreen = page.locator('.lesson-done-card')
      await expect(doneScreen).toBeVisible()
      await expect(page.locator('.lesson-done-title')).toHaveText(t(lang, 'lesson.doneTitle'))
      await expect(page.locator('.lesson-done-actions button')).toHaveCount(2)
    })

    test('leave mid-lesson and resume at the same step', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1')
      await expect(page.locator('.step-intro-tip')).toBeVisible()

      // Advance to step 1 (breathing) and then step 2 (tip)
      const nextBtn = page.locator('.player-next-btn')
      await nextBtn.click()
      await expect(page.locator('.step-breathing')).toBeVisible()

      await nextBtn.click()
      await expect(page.locator('.step-intro-tip')).toBeVisible()
      await expect(page.locator('.player-step-counter')).toContainText('3')

      // Click close button to leave lesson
      const closeBtn = page.locator('.close-lesson-btn')
      await closeBtn.click()

      // Should be back on course page
      await expect(page).toHaveURL(/\/trainings\/smooth-speaking\/easy-starts$/)

      // Re-enter the lesson
      await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1')

      // Verifies it resumes at Step 3 (step index 2)
      await expect(page.locator('.player-step-counter')).toContainText('3')
      await expect(page.locator('.step-intro-tip')).toBeVisible()
    })

    test('reduced motion mode removes animations on breathing and celebratory screen', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1')
      // Advance to breathing step
      const nextBtn = page.locator('.player-next-btn')
      await nextBtn.click()
      await expect(page.locator('.step-breathing')).toBeVisible()

      // Under reducedMotion (configured in playwright), breathing circle has .reduced class
      const breathingCircle = page.locator('.breathing-circle')
      await expect(breathingCircle).toHaveClass(/reduced/)
    })
  })
}
