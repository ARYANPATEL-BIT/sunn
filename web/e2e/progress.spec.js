import {
  expect, expectNoLeaks, LANGS, markOnboarded, openSpeak, QUICK_START, recognizeAndConfirm, signUp, t, test,
} from './helpers.js'

const metric = (page, lang, key) =>
  page.locator('.metric-card').filter({ has: page.getByText(t(lang, key), { exact: true }) }).locator('.metric-value')

for (const lang of LANGS) {
  test.describe(`progress, ${lang}`, () => {
    test.use({ lang })

    test('empty for a new user, then stats and the weekly trend', async ({ page }) => {
      const user = await signUp(page.request, { speaks: lang })
      await markOnboarded(page, user)

      await page.goto('/app/progress')
      await expect(page.getByRole('heading', { name: t(lang, 'progress.nothing') })).toBeVisible()
      await expect(page.getByText(t(lang, 'progress.noActivity'))).toBeVisible()
      await expect(page.getByText(t(lang, 'progress.topPhrasesEmpty'))).toBeVisible()
      await expect(metric(page, lang, 'progress.phrases')).toHaveText('51')
      await expect(metric(page, lang, 'progress.confirmed')).toHaveText('0')
      await expectNoLeaks(page, lang)

      await openSpeak(page.request, user)
      const water = user.phrases.find((p) => p.text === QUICK_START[lang][2])
      for (let i = 0; i < 3; i++) await recognizeAndConfirm(page.request, water.id)

      await page.reload()
      await expect(metric(page, lang, 'progress.teaching')).toHaveText('30')
      await expect(metric(page, lang, 'progress.spoken')).toHaveText('3')
      await expect(metric(page, lang, 'progress.confirmed')).toHaveText('3')
      await expect(page.getByRole('heading', { name: t(lang, 'progress.firstRight') })).toBeVisible()
      await expect(page.locator('.top-phrase-item').filter({ hasText: QUICK_START[lang][2] })).toContainText(
        t(lang, 'progress.usesCount', { count: 3 }),
      )
      await expect(page.getByRole('img', { name: t(lang, 'progress.weeklyDesc') })).toBeVisible()
      await expect(page.getByRole('heading', { name: t(lang, 'progress.nothing') })).toHaveCount(0)
      await expectNoLeaks(page, lang)

      await page.getByRole('button', { name: t(lang, 'progress.weeklyTableToggle') }).click()
      const rows = page.getByRole('table').getByRole('row')
      await expect(rows).toHaveCount(9) // a header and 8 weeks
      await expect(rows.last().getByRole('cell').first()).toHaveText('3')
      await expectNoLeaks(page, lang)
    })
  })
}
