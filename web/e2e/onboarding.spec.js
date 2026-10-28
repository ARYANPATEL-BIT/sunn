import { enroll, expect, expectNoLeaks, LANGS, openSpeak, QUICK_START, signUp, t, test } from './helpers.js'

const other = (code) => (code === 'en' ? 'hi' : 'en')

async function toStep(page, lang, step) {
  await page.goto('/app/onboarding')
  for (let n = 1; n < step; n++) await page.getByRole('button', { name: t(lang, 'onboarding.next') }).click()
  await expect(page.getByText(t(lang, 'onboarding.stepProgress', { current: step, total: 4 })).first()).toBeVisible()
}

for (const lang of LANGS) {
  test.describe(`welcome guide, ${lang}`, () => {
    test.use({ lang })

    test('the language cards change only the screen, never the language spoken', async ({ page }) => {
      const user = await signUp(page.request, { speaks: lang })
      const patches = []
      page.on('request', (r) => r.method() === 'PATCH' && patches.push(r.url()))
      await toStep(page, lang, 2)
      await expect(page.getByRole('heading', { name: t(lang, 'onboarding.langHeading') })).toBeVisible()

      const card = (ui, code) => page.getByRole('radio', { name: t(ui, code === 'hi' ? 'onboarding.langHindi' : 'onboarding.langEnglish') })
      await card(lang, other(lang)).click()
      await expect(page.locator('html')).toHaveAttribute('lang', other(lang))
      await card(other(lang), lang).click()
      await expect(page.locator('html')).toHaveAttribute('lang', lang)

      expect(patches).toEqual([])
      expect((await (await page.request.get('/api/auth/me')).json()).language).toBe(user.language)
    })

    test('the last step says ready only once Speak is open', async ({ page }) => {
      const user = await signUp(page.request, { speaks: lang })
      const first = user.phrases.find((p) => p.text === QUICK_START[lang][0])
      await enroll(page.request, first.id, 3) // one phrase ready is not enough

      await toStep(page, lang, 4)
      await expect(page.getByText(t(lang, 'onboarding.setupNeedTitle'))).toBeVisible()
      await expect(page.getByText(t(lang, 'onboarding.setupReadyTitle'))).toHaveCount(0)
      await expectNoLeaks(page, lang)
      await page.getByRole('button', { name: t(lang, 'onboarding.finish') }).click()
      await expect(page).toHaveURL(/\/app\/enroll$/)

      await openSpeak(page.request, user)
      await toStep(page, lang, 4)
      await expect(page.getByText(t(lang, 'onboarding.setupReadyTitle'))).toBeVisible()
      await page.getByRole('button', { name: t(lang, 'onboarding.finish') }).click()
      await expect(page).toHaveURL(/\/app\/speak$/)
      await expect(page.getByRole('button', { name: t(lang, 'sun.tap') })).toBeVisible()
    })
  })
}
