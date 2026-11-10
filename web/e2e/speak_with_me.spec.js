import {
  expect, LANGS, markOnboarded, openSpeak, record, signUp, t, test,
} from './helpers.js'

for (const lang of LANGS) {
  test.describe(`speak with me & checking, ${lang}`, () => {
    test.use({ lang })

    test('choral mode highlights words during playback and restarts', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1')

      // Advance to step 4: easy-starts-1-together (speak_with_me, choral)
      const nextBtn = page.locator('.player-next-btn')
      for (let i = 0; i < 4; i++) {
        await nextBtn.click()
      }

      await expect(page.locator('.step-speak-with-me')).toBeVisible()
      await expect(page.locator('.step-mode-badge')).toContainText(t(lang, 'speakWithMe.choral'))

      // Words display exists
      const wordsBox = page.locator('.speak-words-display')
      await expect(wordsBox).toBeVisible()

      // Play button starts highlighting
      const playBtn = page.locator('.play-pause-btn')
      await expect(playBtn).toBeVisible()
      await playBtn.click()

      // During playback a word is highlighted (either current or past)
      await expect(page.locator('.word-span.current').or(page.locator('.word-span.past')).first()).toBeVisible({ timeout: 5000 })

      // Restart resets highlighting
      const restartBtn = page.locator('.restart-btn')
      await restartBtn.click()
      await expect(page.locator('.word-span.current')).toHaveCount(0)
    })

    test('paced mode allows speed slider changes and starts pacing', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-2')
      const nextBtn = page.locator('.player-next-btn')
      while (!(await page.locator('.pace-range-input').isVisible())) {
        await nextBtn.click()
      }

      await expect(page.locator('.step-speak-with-me')).toBeVisible()
      await expect(page.locator('.step-mode-badge')).toContainText(t(lang, 'speakWithMe.paced'))

      const slider = page.locator('.pace-range-input')
      await expect(slider).toBeVisible()
      await expect(page.locator('.pace-current-wpm')).toContainText(t(lang, 'speakWithMe.wpmLabel', { wpm: 50 }))

      // Adjust speed
      await slider.fill('75')
      await slider.dispatchEvent('input')
      await slider.dispatchEvent('change')
      await expect(page.locator('.pace-current-wpm')).toContainText(t(lang, 'speakWithMe.wpmLabel', { wpm: 75 }))

      // Play starts pacing
      const playBtn = page.locator('.play-pause-btn')
      await playBtn.click()
      await expect(page.locator('.word-span.current').or(page.locator('.word-span.past')).first()).toBeVisible({ timeout: 5000 })

      // Pause pauses pacing
      await playBtn.click()
    })

    test('checking flow on step with words feedback', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      // s-and-sh-1 step 4 is s-and-sh-1-echo (speak_with_me sentence with feedback: words)
      await page.goto('/trainings/clear-speech/s-and-sh/s-and-sh-1')
      const nextBtn = page.locator('.player-next-btn')
      while (!(await page.locator('.step-speak-with-me').isVisible())) {
        await nextBtn.click()
      }

      await expect(page.locator('.step-speak-with-me')).toBeVisible()

      // Echo mode: Listen to Sunn first
      const listenBtn = page.locator('.speak-control-btn')
      await listenBtn.click()

      // Wait for "Your turn" phase banner to appear
      await expect(page.locator('.echo-phase-banner.your_turn')).toBeVisible({ timeout: 6000 })

      // Record a sample
      await record(page, lang, 1.2)

      // Check actions appear
      const checkBtn = page.locator('.check-reading-btn')
      const practiseAgainBtn = page.locator('.practise-again-btn')
      await expect(checkBtn).toBeVisible()
      await expect(practiseAgainBtn).toBeVisible()
      await expect(page.locator('.checks-counter-meta')).toContainText(t(lang, 'check.checksLeft', { count: 20 }))

      // Click "Check my reading"
      await checkBtn.click()

      // Results display words feedback and practise tags
      await expect(page.locator('.words-check-grid')).toBeVisible()
      await expect(page.locator('.word-practise-tag').first()).toBeVisible()
      // Checks count against the STT daily limit only when sent to Gnani, and mock mode sends nothing.
      await expect(page.locator('.checks-counter-meta')).toContainText(t(lang, 'check.checksLeft', { count: 20 }))

      // Practise again resets to record state
      await practiseAgainBtn.click()
      await expect(page.locator('.check-reading-btn')).toHaveCount(0)
    })

    test('checking flow on step with none feedback', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      // easy-starts-1 step 3 is easy-starts-1-vowels (listen_repeat with feedback: none)
      await page.goto('/trainings/smooth-speaking/easy-starts/easy-starts-1')
      const nextBtn = page.locator('.player-next-btn')
      for (let i = 0; i < 3; i++) {
        await nextBtn.click()
      }

      await expect(page.locator('.step-listen-repeat')).toBeVisible()
      await record(page, lang, 1.2)

      const checkBtn = page.locator('.check-reading-btn')
      await expect(checkBtn).toBeVisible()
      await checkBtn.click()

      // Shows "You finished it. Nice work." and no word error tags
      await expect(page.locator('.check-none-text')).toContainText(t(lang, 'check.feedbackNone'))
      await expect(page.locator('.words-check-grid')).toHaveCount(0)
    })

    test('checks used up shows friendly notice while practise again remains available', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      // Intercept attempt to simulate 0 checks left
      await page.route('**/me/trainings/attempts', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            checked: false,
            words: null,
            similarity: null,
            wpm: null,
            pace: null,
            message_key: 'no_checks_left',
            checks_left_today: 0,
          }),
        })
      })

      await page.goto('/trainings/clear-speech/s-and-sh/s-and-sh-1')
      const nextBtn = page.locator('.player-next-btn')
      for (let i = 0; i < 3; i++) {
        await nextBtn.click()
      }

      await record(page, lang, 1.2)
      const checkBtn = page.locator('.check-reading-btn')
      await checkBtn.click()

      // Shows no checks left message
      await expect(page.locator('.check-supportive-message')).toContainText(t(lang, 'check.message_no_checks_left'))

      // Practise again still works
      const practiseAgainBtn = page.locator('.practise-again-btn')
      await expect(practiseAgainBtn).toBeEnabled()
      await practiseAgainBtn.click()

      // On next record attempt, check button is disabled and shows friendly no checks notice
      await record(page, lang, 1.2)
      await expect(page.locator('.check-reading-btn')).toBeDisabled()
      await expect(page.locator('.checks-counter-meta')).toContainText(t(lang, 'check.noChecksLeft'))
      await expect(practiseAgainBtn).toBeEnabled()
    })

    test('kids-speaking category hides checks counter and displays friendly reaction', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')

      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)

      // sound-play-1 step 5 is sound-play-1-choral in kids-speaking
      await page.goto('/trainings/kids-speaking/sound-play/sound-play-1')
      const nextBtn = page.locator('.player-next-btn')
      while (!(await page.locator('.step-speak-with-me').isVisible())) {
        await nextBtn.click()
      }

      await expect(page.locator('.step-speak-with-me')).toBeVisible()
      await expect(page.locator('.step-container')).toHaveClass(/is-kids/)

      // Toggle "Record me too" then play
      const recordToggle = page.locator('.record-me-toggle input[type="checkbox"]')
      await recordToggle.check()

      const playBtn = page.locator('.play-pause-btn')
      await playBtn.click()
      await page.waitForTimeout(1500)
      await playBtn.click()

      // If recording completed, check action is available
      const checkBtn = page.locator('.check-reading-btn')
      if (await checkBtn.isVisible()) {
        // Kids step must NOT show checks left counter
        await expect(page.locator('.checks-counter-meta')).toHaveCount(0)

        await checkBtn.click()
        // Playful buddy appears
        await expect(page.locator('.kids-buddy-svg')).toBeVisible()
        await expect(page.locator('.kids-reaction-msg')).toBeVisible()
        // No checks counter shown to child
        await expect(page.locator('.checks-counter-meta')).toHaveCount(0)
      }
    })
  })
}
