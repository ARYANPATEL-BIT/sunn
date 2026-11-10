import { expect, expectNoLeaks, LANGS, openSpeak, refuseOnce, signUp, t, test } from './helpers.js'

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

    test('an unknown email is offered a new account', async ({ page, watch }) => {
      watch.allow(401, '/api/auth/me')
      watch.allow(401, '/api/auth/login')
      await page.goto('/login')
      await page.getByLabel(t(lang, 'auth.email')).fill(`e2e-nobody-${Date.now()}@example.com`)
      await page.getByLabel(t(lang, 'auth.password'), { exact: true }).fill('any-password-1')
      await page.getByRole('button', { name: t(lang, 'login.submit') }).click()
      const alert = page.getByRole('alert')
      await expect(alert).toHaveText(`${t(lang, 'error.no_account')} ${t(lang, 'login.createOne')}`)
      await expectNoLeaks(page, lang)
      await alert.getByRole('link', { name: t(lang, 'login.createOne') }).click()
      await expect(page).toHaveURL(/\/signup$/)
    })
  })
}

test.describe('signup page typography and layout', () => {
  test('signup password helper text and form hints have compact typography', async ({ page, watch }) => {
    watch.allow(401, '/api/auth/me')
    await page.goto('/signup')

    const hint = page.locator('#signup-password-hint')
    await expect(hint).toBeVisible()
    await expect(hint).toHaveText('At least 8 characters.')

    const styles = await hint.evaluate((el) => {
      const cs = window.getComputedStyle(el)
      return {
        fontSize: parseFloat(cs.fontSize),
        fontWeight: cs.fontWeight,
        textAlign: cs.textAlign,
        paddingTop: parseFloat(cs.paddingTop),
        paddingBottom: parseFloat(cs.paddingBottom),
      }
    })

    // The helper text must be compact (approx 14px / 0.875rem), not headline clamp (32px to 56px)
    expect(styles.fontSize).toBeLessThanOrEqual(16)
    expect(styles.fontSize).toBeGreaterThanOrEqual(12)
    expect(styles.fontWeight).toMatch(/^(400|normal)$/)
    expect(styles.textAlign).not.toBe('center')
    expect(styles.paddingTop).toBeLessThan(10)

    // Form hint under submit button should also be compact
    const consentHint = page.locator('#consent-needed')
    await expect(consentHint).toBeVisible()
    const consentHintFontSize = await consentHint.evaluate((el) => parseFloat(window.getComputedStyle(el).fontSize))
    expect(consentHintFontSize).toBeLessThanOrEqual(16)
    expect(consentHintFontSize).toBeGreaterThanOrEqual(12)

    // Visual hierarchy: language fieldset is positioned directly under fields
    const fieldsBox = await page.locator('.auth-form .fields').boundingBox()
    const languageBox = await page.locator('.auth-form .group-wrap').first().boundingBox()
    expect(fieldsBox).not.toBeNull()
    expect(languageBox).not.toBeNull()
    expect(languageBox.y - (fieldsBox.y + fieldsBox.height)).toBeLessThanOrEqual(50)
  })

  test('signup password hint retains compact typography in dark mode and during validation errors', async ({ page, watch }) => {
    watch.allow(401, '/api/auth/me')
    await page.goto('/signup')

    // Switch to dark theme
    await page.evaluate(() => {
      document.documentElement.dataset.theme = 'dark'
    })

    const hint = page.locator('#signup-password-hint')
    const darkFontSize = await hint.evaluate((el) => parseFloat(window.getComputedStyle(el).fontSize))
    expect(darkFontSize).toBeLessThanOrEqual(16)

    // Trigger validation error on short password
    await page.locator('#signup-name').fill('Test User')
    await page.locator('#signup-email').fill('test@example.com')
    await page.locator('#signup-password').fill('short')
    await page.getByLabel(t('en', 'signup.consent')).check()
    await page.getByRole('button', { name: t('en', 'signup.submit') }).click()

    // Hint is still compact alongside error
    const err = page.locator('#signup-password-error')
    await expect(err).toBeVisible()
    const hintAfterError = await hint.evaluate((el) => parseFloat(window.getComputedStyle(el).fontSize))
    expect(hintAfterError).toBeLessThanOrEqual(16)
  })
})

