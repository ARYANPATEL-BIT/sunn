import { enroll, expect, expectNoLeaks, INVITE, LANGS, phraseCard, QUICK_START, record, refuseOnce, t, test } from './helpers.js'

// Counts audio that really started playing, whatever made the Audio element.
const COUNT_PLAYBACK = () => {
  const play = HTMLMediaElement.prototype.play
  HTMLMediaElement.prototype.play = function () {
    this.addEventListener('playing', () => (window.__played = (window.__played || 0) + 1), { once: true })
    return play.call(this)
  }
}
const played = (page) => page.evaluate(() => window.__played || 0)
// The recording's form body isn't visible to the test (it holds a Blob), but the answer says
// which context the server got.
const recognizedContext = async (response) => (await (await response).json()).context

const NEW_PHRASE = { en: 'Please open the window', hi: 'खिड़की खोल दो' }

for (const lang of LANGS) {
  test.describe(`new user, ${lang}`, () => {
    test.use({ lang })

    test('sign up with an invite, onboarding, quick start, speak, correct, see it in the library', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')
      await page.addInitScript(COUNT_PLAYBACK)

      // --- sign up: the invite field shows because GET /api/config says it is needed
      await page.goto('/signup')
      const invite = page.getByLabel(t(lang, 'signup.inviteCode'))
      await expect(invite).toBeVisible()
      await expectNoLeaks(page, lang)
      const email = `e2e-journey-${lang}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@example.com`
      await page.getByLabel(t(lang, 'signup.name')).fill(lang === 'hi' ? 'आशा' : 'Asha')
      await page.getByLabel(t(lang, 'auth.email')).fill(email)
      await page.getByLabel(t(lang, 'auth.password'), { exact: true }).fill('e2e-password-1')
      await page.getByRole('checkbox', { name: t(lang, 'signup.consent') }).check()
      const submit = page.getByRole('button', { name: t(lang, 'signup.submit') })

      // The server's own refusal of a wrong code is auth.spec.js's; here, how the app words it.
      await refuseOnce(page, watch, '/api/auth/signup', 403, { error: 'invite_required' })
      await invite.fill('not-the-code')
      await submit.click()
      await expect(page.getByText(t(lang, 'error.invite_required'))).toBeVisible()
      await expect(invite).toBeFocused()

      await refuseOnce(page, watch, '/api/auth/signup', 429, { error: 'too_many_attempts', retry_after: 600 })
      await submit.click()
      await expect(page.getByRole('alert')).toHaveText(t(lang, 'error.too_many_attempts', { minutes: 10 }))

      const signedUp = page.waitForRequest('**/api/auth/signup')
      await invite.fill(INVITE)
      await submit.click()
      expect((await signedUp).postDataJSON()).toMatchObject({ invite_code: INVITE, language: lang, consent: true })

      // --- onboarding: four steps, then Teach, since nothing is recorded yet
      await expect(page).toHaveURL(/\/app\/onboarding$/)
      for (let step = 1; step < 4; step++) {
        await expect(page.getByText(t(lang, 'onboarding.stepProgress', { current: step, total: 4 })).first()).toBeVisible()
        // Step 2 shows each language's greeting in its own script; that is the point of it.
        if (step !== 2) await expectNoLeaks(page, lang)
        await page.getByRole('button', { name: t(lang, 'onboarding.next') }).click()
      }
      await expect(page.getByText(t(lang, 'onboarding.setupNeedTitle'))).toBeVisible()
      await page.getByRole('button', { name: t(lang, 'onboarding.finish') }).click()

      // --- Teach: the 10 quick-start phrases first, with the line saying so
      await expect(page).toHaveURL(/\/app\/enroll$/)
      await expect(page.getByText(t(lang, 'enroll.quickStart'))).toBeVisible()
      await expect(page.getByRole('heading', { level: 1 })).toContainText(QUICK_START[lang][0])
      await expectNoLeaks(page, lang)
      await record(page, lang)
      await page.getByRole('button', { name: t(lang, 'enroll.play') }).click()
      await expect.poll(() => played(page)).toBeGreaterThan(0)
      const saved = page.waitForResponse((r) => r.url().endsWith('/api/me/enroll'))
      await page.getByRole('button', { name: t(lang, 'enroll.save') }).click()
      expect((await saved).status()).toBe(200)
      await expect(page.getByRole('img', { name: t(lang, 'enroll.saved', { n: 1, needed: 3 }) })).toBeVisible()

      // Speak stays closed until all 10 have 3 recordings.
      await page.getByRole('link', { name: t(lang, 'tab.speak') }).click()
      await expect(page.getByRole('heading', { name: t(lang, 'speak.none') })).toBeVisible()
      await expect(page.getByText(t(lang, 'speak.noneBody', { n: 0, total: 10 }))).toBeVisible()
      await expectNoLeaks(page, lang)

      // The other 29 recordings through the API, as the screen would send them.
      const phrases = await (await page.request.get('/api/me/phrases')).json()
      for (const text of QUICK_START[lang]) {
        const phrase = phrases.find((p) => p.text === text)
        await enroll(page.request, phrase.id, 3 - phrase.sample_count)
      }
      await page.getByRole('link', { name: t(lang, 'tab.enroll') }).click()
      await expect(page.getByText(t(lang, 'enroll.quickDone'))).toBeVisible()

      // --- Speak: the chosen context goes with the recording; Any sends none
      await page.getByRole('link', { name: t(lang, 'tab.speak') }).click()
      await page.getByRole('radio', { name: t(lang, 'speak.context_home') }).click()
      await expect(page.getByRole('radio', { name: t(lang, 'speak.context_home') })).toHaveAttribute('aria-checked', 'true')
      let recognized = page.waitForResponse((r) => r.url().endsWith('/api/me/recognize'))
      await record(page, lang)
      expect(await recognizedContext(recognized)).toBe('home')

      const candidates = page.locator('.candidate')
      await expect(candidates.first()).toBeVisible()
      await expectNoLeaks(page, lang)
      const before = await played(page)
      const confirmed = page.waitForRequest('**/api/me/confirm')
      const spoken = page.waitForResponse((r) => r.url().endsWith('/api/speak'))
      await candidates.first().click()
      expect((await confirmed).postDataJSON()).toHaveProperty('phrase_id')
      const audio = await spoken
      expect(audio.status()).toBe(200)
      expect(audio.headers()['content-type']).toContain('audio/wav')
      await expect.poll(() => played(page)).toBeGreaterThan(before)
      await expect(page.getByText(t(lang, 'speak.played'))).toBeVisible()
      await expect(page.getByText(t(lang, 'speak.usingBrowserTts'))).toHaveCount(0)

      // --- none of these: type the phrase, which is said and becomes a phrase
      await page.getByRole('radio', { name: t(lang, 'speak.context_any') }).click()
      recognized = page.waitForResponse((r) => r.url().endsWith('/api/me/recognize'))
      await record(page, lang)
      expect(await recognizedContext(recognized)).toBeNull()
      await page.getByRole('button', { name: t(lang, 'speak.noneOfThese') }).click()
      await page.getByLabel(t(lang, 'speak.typeLabel')).fill(NEW_PHRASE[lang])
      const corrected = page.waitForRequest('**/api/me/confirm')
      const said = page.waitForResponse((r) => r.url().endsWith('/api/speak'))
      await page.getByRole('button', { name: t(lang, 'speak.sayIt') }).click()
      expect((await corrected).postDataJSON()).toMatchObject({ new_text: NEW_PHRASE[lang] })
      expect((await said).status()).toBe(200)

      await page.getByRole('link', { name: t(lang, 'tab.phrases') }).click()
      await page.getByRole('searchbox').fill(NEW_PHRASE[lang])
      await expect(phraseCard(page, NEW_PHRASE[lang])).toBeVisible()
      await expectNoLeaks(page, lang)
    })
  })
}
