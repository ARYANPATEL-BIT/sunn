import { expect, expectNoLeaks, INVITE, LANGS, openSpeak, refuseOnce, signUp, t, test } from './helpers.js'

const PROTECTED = ['/app/speak', '/app/enroll', '/app/phrases', '/app/progress', '/app/settings', '/app/onboarding']

for (const lang of LANGS) {
  test.describe(`signed out, ${lang}`, () => {
    test.use({ lang })

    test('landing, start speaking, sign in, back to speak', async ({ page, request, watch }) => {
      watch.allow(401, '/api/auth/me') // the session check before anyone signs in
      const user = await signUp(request, { speaks: lang })
      await openSpeak(request, user)

      await page.goto('/')
      // The headline is the English one in every language, with the interface language under it.
      await expect(page.getByRole('heading', { level: 1 })).toHaveText(t('en', 'hero.headline'))
      await expect(page.locator('.display-other')).toHaveText(t(lang === 'en' ? 'hi' : lang, 'hero.headline'))
      await expectNoLeaks(page, lang)
      await page.getByRole('button', { name: t(lang, 'cta.start') }).first().click()
      await expect(page).toHaveURL(/\/login\?next=%2Fapp%2Fspeak$/)
      await expectNoLeaks(page, lang)

      await page.getByLabel(t(lang, 'auth.email')).fill(user.email)
      await page.getByLabel(t(lang, 'auth.password'), { exact: true }).fill(user.password)
      await page.getByRole('button', { name: t(lang, 'login.submit') }).click()
      await expect(page).toHaveURL(/\/app\/speak$/)
      await expect(page.getByRole('button', { name: t(lang, 'sun.tap') })).toBeVisible()
      await expectNoLeaks(page, lang)
    })

    test('protected routes send to login with next', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')
      for (const path of PROTECTED) {
        await page.goto(path)
        await expect(page).toHaveURL(`/login?next=${encodeURIComponent(path)}`)
      }
      await expectNoLeaks(page, lang)
    })

    test('wrong password and locked login are said in plain words', async ({ page, request, watch }) => {
      watch.allow(401, '/api/auth/me')
      watch.allow(401, '/api/auth/login')
      watch.allow(429, '/api/auth/login')
      const user = await signUp(request, { speaks: lang })
      await page.goto('/login')
      await page.getByLabel(t(lang, 'auth.email')).fill(user.email)
      await page.getByLabel(t(lang, 'auth.password'), { exact: true }).fill('not the password')
      await page.getByRole('button', { name: t(lang, 'login.submit') }).click()
      await expect(page.getByRole('alert')).toHaveText(t(lang, 'error.bad_login'))

      // Five wrong tries lock the email for 15 minutes; that answer, faked.
      await refuseOnce(page, watch, '/api/auth/login', 429, { error: 'too_many_attempts', retry_after: 600 })
      await page.getByRole('button', { name: t(lang, 'login.submit') }).click()
      await expect(page.getByRole('alert')).toHaveText(t(lang, 'error.too_many_attempts', { minutes: 10 }))
      await expectNoLeaks(page, lang)
    })
  })
}

// The one real wrong invite code of a run: the server counts them per address, and five lock
// sign-up for every test after.
test('the server refuses a wrong invite code, and the app says so', async ({ page, watch }, info) => {
  test.skip(info.project.name !== 'phone', 'once per run')
  watch.allow(401, '/api/auth/me')
  watch.allow(403, '/api/auth/signup')
  await page.goto('/signup')
  await page.getByLabel(t('en', 'signup.name')).fill('Asha')
  await page.getByLabel(t('en', 'auth.email')).fill(`e2e-wrong-invite-${Date.now()}@example.com`)
  await page.getByLabel(t('en', 'auth.password'), { exact: true }).fill('e2e-password-1')
  await page.getByLabel(t('en', 'signup.inviteCode')).fill(`not-${INVITE}`)
  await page.getByRole('checkbox', { name: t('en', 'signup.consent') }).check()
  const refused = page.waitForResponse((r) => r.url().endsWith('/api/auth/signup'))
  await page.getByRole('button', { name: t('en', 'signup.submit') }).click()
  expect((await refused).status()).toBe(403)
  await expect(page.getByText(t('en', 'error.invite_required'))).toBeVisible()
  await expect(page).toHaveURL(/\/signup$/)
})
