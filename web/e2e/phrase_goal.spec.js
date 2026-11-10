import { enroll, expect, signUp, t, test } from './helpers.js'

test.describe('dynamic phrase onboarding goal', () => {
  test('Scenario 0: new user starts with no goal; Speak shows intro, not 0 of 10; Record phrases opens goal selection', async ({ page }) => {
    const user = await signUp(page.request, { speaks: 'en' })

    // Visit /app/speak directly as a brand new user
    await page.goto('/app/speak')

    // Verifies introductory text is displayed
    await expect(page.getByRole('heading', { name: t('en', 'speak.chooseGoalTitle') })).toBeVisible()
    await expect(page.getByText(t('en', 'speak.chooseGoalSubtitle'))).toBeVisible()
    const recordPhrasesBtn = page.getByRole('button', { name: t('en', 'speak.recordPhrases') })
    await expect(recordPhrasesBtn).toBeVisible()

    // Verifies that misleading defaults are NOT displayed
    await expect(page.getByText('0 of 10 are ready')).toHaveCount(0)
    await expect(page.getByText('0 / 10')).toHaveCount(0)
    await expect(page.getByText('10 selected')).toHaveCount(0)

    // Click Record phrases opens goal selection at /app/enroll
    await recordPhrasesBtn.click()
    await expect(page).toHaveURL(/\/app\/enroll$/)
    await expect(page.getByRole('heading', { name: t('en', 'enroll.goalTitle') })).toBeVisible()

    // Confirm 10 phrases goal
    await page.getByRole('button', { name: t('en', 'enroll.goalContinue') }).click()

    // Teach now reflects 0 / 10
    await expect(page.getByText('0 / 10')).toBeVisible()

    // Returning to Speak now reflects 0 of 10
    await page.goto('/app/speak')
    await expect(page.getByText(t('en', 'speak.noneBody', { n: 0, total: 10 }))).toBeVisible()

    // Persists across reload
    await page.reload()
    await expect(page.getByText(t('en', 'speak.noneBody', { n: 0, total: 10 }))).toBeVisible()
  })

  test('Scenario A: new user selects 10 phrases goal and records first phrase', async ({ page }) => {
    const user = await signUp(page.request, { speaks: 'en' })
    await page.goto('/app/enroll')

    // Goal selector appears for new user with 0 ready phrases
    await expect(page.getByRole('heading', { name: t('en', 'enroll.goalTitle') })).toBeVisible()
    await expect(page.getByRole('button', { name: t('en', 'enroll.goalContinue') })).toBeVisible()

    // Confirm default 10 goal
    await page.getByRole('button', { name: t('en', 'enroll.goalContinue') }).click()

    // Teach screen is displayed with 0 / 10 progress
    await expect(page.getByText('0 / 10')).toBeVisible()
    await expect(page.getByText(t('en', 'enroll.step', { n: 1, total: 10 }))).toBeVisible()
    await expect(page.getByText(t('en', 'enroll.goalChange'))).toBeVisible()

    // Enroll phrase 1 once (1 of 3)
    const firstPhrase = user.phrases[0]
    await enroll(page.request, firstPhrase.id, 1)
    await page.reload()

    // Saved meter shows 1 of 3, still phrase 1 of 10
    await expect(page.getByText('1 / 3')).toBeVisible()
    await expect(page.getByText(t('en', 'enroll.step', { n: 1, total: 10 }))).toBeVisible()

    // Enroll 2 more times to make phrase 1 ready
    await enroll(page.request, firstPhrase.id, 2)
    await page.reload()

    // Progress updates to 1 / 10 and advances to phrase 2 of 10
    await expect(page.getByText('1 / 10')).toBeVisible()
    await expect(page.getByText(t('en', 'enroll.step', { n: 2, total: 10 }))).toBeVisible()
  })

  test('Scenario B: user chooses 20 goal and both Speak and Teach reflect 20', async ({ page }) => {
    const user = await signUp(page.request, { speaks: 'hi' })
    await page.goto('/app/enroll')

    // Goal selector appears
    await expect(page.getByRole('heading', { name: t('en', 'enroll.goalTitle') })).toBeVisible()

    // Select 20 phrases
    const opt20 = page.getByRole('radio', { name: t('en', 'enroll.goalCount', { count: 20 }) })
    await opt20.click()
    await page.getByRole('button', { name: t('en', 'enroll.goalContinue') }).click()

    // Teach screen shows 0 / 20 (not 0 / 51)
    await expect(page.getByText('0 / 20')).toBeVisible()
    await expect(page.getByText(t('en', 'enroll.step', { n: 1, total: 20 }))).toBeVisible()

    // Check Speak screen also reflects 0 of 20
    await page.goto('/app/speak')
    await expect(page.getByText(t('en', 'speak.noneBody', { n: 0, total: 20 }))).toBeVisible()
  })

  test('Scenario C: user changes goal via Change goal button and Settings', async ({ page }) => {
    const user = await signUp(page.request, { speaks: 'en' })
    await page.goto('/app/enroll')

    // Initial goal selection
    await page.getByRole('button', { name: t('en', 'enroll.goalContinue') }).click()
    await expect(page.getByText('0 / 10')).toBeVisible()

    // Click Change goal button
    await page.getByText(t('en', 'enroll.goalChange')).click()
    await expect(page.getByRole('heading', { name: t('en', 'enroll.goalTitle') })).toBeVisible()

    // Select 30
    await page.getByRole('radio', { name: t('en', 'enroll.goalCount', { count: 30 }) }).click()
    await page.getByRole('button', { name: t('en', 'enroll.goalContinue') }).click()

    // Now Teach shows 0 / 30
    await expect(page.getByText('0 / 30')).toBeVisible()
    await expect(page.getByText(t('en', 'enroll.step', { n: 1, total: 30 }))).toBeVisible()

    // Verify in Settings page
    await page.goto('/app/settings')
    await expect(page.getByRole('heading', { name: t('en', 'settings.phraseGoalTitle') })).toBeVisible()
    const radio30 = page.getByRole('radio', { name: t('en', 'enroll.goalCount', { count: 30 }) })
    await expect(radio30).toHaveAttribute('aria-checked', 'true')
  })

  test('Scenario D: goal completion unlocks Speak mode and offers Prepare more phrases', async ({ page }) => {
    const user = await signUp(page.request, { speaks: 'en' })

    // User chooses 10 phrases
    await page.request.patch('/api/me', { data: { phrase_goal: 10 } })

    // Enroll all 10 starter phrases to complete initial goal
    for (const text of ['I need help', "I'm in pain", 'I need water', 'I need the bathroom', 'Give me my medicine',
      'Call the doctor', "I can't breathe properly", "I'm hungry", 'I feel cold', 'Help me sit up']) {
      const phrase = user.phrases.find((p) => p.text === text)
      if (phrase) {
        await enroll(page.request, phrase.id, 3)
      }
    }

    await page.goto('/app/enroll')

    // Shows initial preparation complete
    await expect(page.getByRole('heading', { name: t('en', 'enroll.goalDoneTitle') })).toBeVisible()
    await expect(page.getByRole('button', { name: t('en', 'enroll.prepareMore') })).toBeVisible()

    // Speak mode is unlocked
    await page.getByRole('button', { name: t('en', 'enroll.goSpeak') }).click()
    await expect(page).toHaveURL(/\/app\/speak$/)
    await expect(page.getByRole('button', { name: t('en', 'sun.tap') })).toBeVisible()
  })
})
