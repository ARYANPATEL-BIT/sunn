import {
  enroll, expect, expectNoLeaks, LANGS, markOnboarded, openPhrase, phraseCard, QUICK_START, signUp, t, test,
} from './helpers.js'

const SUFFIX = { en: ' now', hi: ' अभी' }

for (const lang of LANGS) {
  test.describe(`phrase library, ${lang}`, () => {
    test.use({ lang })

    test('edit, mark urgent, delete with a confirm, and label simulated speech', async ({ page }) => {
      const user = await signUp(page.request, { speaks: lang })
      await markOnboarded(page, user)
      const text = QUICK_START[lang][2] // "I need water", not urgent by default
      const water = user.phrases.find((p) => p.text === text)
      await enroll(page.request, water.id, 1, 'simulated') // a demo recording, as scripts/load_demo.py makes

      await page.goto('/app/phrases')
      await expect(page.getByRole('heading', { level: 1, name: t(lang, 'phrases.title') })).toBeVisible()
      await expect(page.getByText(t(lang, 'phrases.total', { count: 51 }))).toBeVisible()
      await page.getByRole('searchbox').fill(text)
      const card = phraseCard(page, text)
      await expect(card).toHaveCount(1)
      await expect(card.getByText(t(lang, 'demo.sourceBadge_simulated'))).toBeVisible()
      await expect(card.getByText(t(lang, 'phrases.enrolledStatus', { enrolled: 1, needed: 3 }))).toBeVisible()
      await expect(card.getByText(t(lang, 'speak.urgent'), { exact: true })).toHaveCount(0)
      await expectNoLeaks(page, lang)

      // Edit the text and mark it urgent, from the phrase's details.
      await openPhrase(page, text)
      await card.getByRole('button', { name: `${t(lang, 'phrases.edit')}: ${text}` }).click()
      const edited = text + SUFFIX[lang]
      await page.getByLabel(t(lang, 'phrases.textLabel'), { exact: true }).fill(edited)
      await page.getByRole('checkbox', { name: t(lang, 'phrases.urgentLabel') }).check()
      const patched = page.waitForRequest((r) => r.method() === 'PATCH' && r.url().includes('/api/me/phrases/'))
      await page.getByRole('button', { name: t(lang, 'phrases.save') }).click()
      expect((await patched).postDataJSON()).toMatchObject({ text: edited, urgent: true })
      await expect(page.getByText(t(lang, 'phrases.updatedSuccess'))).toBeVisible()
      const editedCard = phraseCard(page, edited)
      await expect(editedCard.getByText(t(lang, 'speak.urgent'), { exact: true })).toBeVisible()
      await expectNoLeaks(page, lang)

      // Delete asks first; keeping it changes nothing.
      await openPhrase(page, edited)
      const deleteButton = editedCard.getByRole('button', { name: `${t(lang, 'phrases.delete')}: ${edited}` })
      await deleteButton.click()
      await expect(page.getByRole('heading', { name: t(lang, 'phrases.deleteConfirm', { text: edited }) })).toBeVisible()
      await expectNoLeaks(page, lang)
      await page.getByRole('button', { name: t(lang, 'phrases.deleteNo') }).click()
      await expect(editedCard).toHaveCount(1)
      await deleteButton.click()
      const deleted = page.waitForResponse((r) => r.request().method() === 'DELETE')
      await page.getByRole('button', { name: t(lang, 'phrases.deleteYes') }).click()
      expect((await deleted).status()).toBe(200)
      await expect(page.getByText(t(lang, 'phrases.deletedSuccess'))).toBeVisible()
      await expect(editedCard).toHaveCount(0)
      await page.getByRole('searchbox').fill('')
      await expect(page.getByText(t(lang, 'phrases.total', { count: 50 }))).toBeVisible()
    })
  })
}
