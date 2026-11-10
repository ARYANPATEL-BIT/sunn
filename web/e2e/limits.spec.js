// What the app says when one of the account's daily speech limits is used up (docs/API.md,
// GET /me/usage). The e2e server runs in mock mode, which sends nothing to Gnani and so never
// reaches a limit; the 429 is faked, and tests/test_limits.py checks the server's side.
import { language } from '../src/i18n/languages.js'
import { expect, expectNoLeaks, LANGS, markOnboarded, openSpeak, record, refuseOnce, signUp, t, test } from './helpers.js'

const RESETS_AT = '2026-11-11T11:00:00+00:00'
const limitHit = (kind, limit) => ({ error: 'daily_limit', kind, limit, used: limit, resets_at: RESETS_AT })

// The reset time as the page writes it: in the interface language, in the browser's time zone.
const resetTime = (page, lang) =>
  page.evaluate(([at, locale]) => new Date(at).toLocaleTimeString(locale, { hour: 'numeric', minute: '2-digit' }),
    [RESETS_AT, language(lang).locale])

for (const lang of LANGS) {
  test.describe(`daily limits, ${lang}`, () => {
    test.use({ lang })

    test('speak: no recordings left says so calmly, and the rest still works', async ({ page, watch }) => {
      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)
      await page.goto('/app/speak')

      await refuseOnce(page, watch, '/api/me/recognize', 429, limitHit('stt', 20))
      await record(page, lang)
      const time = await resetTime(page, lang)
      await expect(page.getByRole('alert')).toHaveText(t(lang, 'error.daily_limit_stt', { limit: 20, time }))
      await expect(page.getByRole('button', { name: t(lang, 'speak.retry') })).toHaveCount(0)
      await expectNoLeaks(page, lang, [time])

      await page.getByRole('link', { name: t(lang, 'tab.phrases') }).click()
      await expect(page.getByText(t(lang, 'phrases.total', { count: 51 }))).toBeVisible()
    })

    test('speak: nothing left to say aloud shows the phrase big instead', async ({ page, watch }) => {
      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)
      await page.goto('/app/speak')
      await record(page, lang)
      const top = page.locator('.candidate.top')
      await expect(top).toBeVisible()
      const text = (await top.locator('.candidate-text').textContent()).trim()

      await refuseOnce(page, watch, '/api/speak', 429, limitHit('tts', 20))
      await top.click()
      const shown = page.getByRole('dialog', { name: text })
      await expect(shown.locator('.listener-text')).toHaveText(text)
      const time = await resetTime(page, lang)
      await expect(shown.getByRole('alert')).toHaveText(t(lang, 'error.daily_limit_tts', { limit: 20, time }))
      await expect(page.getByText(t(lang, 'speak.usingBrowserTts'))).toHaveCount(0) // not spoken some other way
      await expectNoLeaks(page, lang, [time])
      await shown.getByRole('button', { name: t(lang, 'sheet.close') }).click()
      await expect(shown).toHaveCount(0)
    })

    test('teaching phrases: the setup limit says so calmly', async ({ page, watch }) => {
      const user = await signUp(page.request, { speaks: lang })
      await page.request.patch('/api/me', { data: { phrase_goal: 10 } })
      await markOnboarded(page, user)
      await page.goto('/app/enroll')
      await record(page, lang)
      await refuseOnce(page, watch, '/api/me/enroll', 429, limitHit('enroll', 40))
      await page.getByRole('button', { name: t(lang, 'enroll.save') }).click()
      const time = await resetTime(page, lang)
      await expect(page.getByRole('alert')).toHaveText(t(lang, 'error.daily_limit_enroll', { limit: 40, time }))
      await expectNoLeaks(page, lang, [time])
    })

    test('settings shows what is used of each limit', async ({ page }) => {
      const user = await signUp(page.request, { speaks: lang })
      await markOnboarded(page, user)
      await page.route('**/api/me/usage', (route) => route.fulfill({ json: {
        stt: { used: 7, limit: 20, resets_at: RESETS_AT }, tts: { used: 3, limit: 20, resets_at: RESETS_AT },
        enroll: { used: 12, limit: 40, resets_at: RESETS_AT } } }))
      await page.goto('/app/settings')
      await expect(page.getByText(t(lang, 'settings.usageStt', { used: 7, limit: 20 }))).toBeVisible()
      await expect(page.getByText(t(lang, 'settings.usageTts', { used: 3, limit: 20 }))).toBeVisible()
      await expect(page.getByText(t(lang, 'settings.usageEnroll', { used: 12, limit: 40 }))).toBeVisible()
      await expectNoLeaks(page, lang)
    })
  })
}
