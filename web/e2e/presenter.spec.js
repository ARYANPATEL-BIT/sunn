import { expect, markOnboarded, signUp, t, test } from './helpers.js'

test('presenter mode opens from the header, steps through the screens and closes', async ({ page }) => {
  const user = await signUp(page.request)
  await markOnboarded(page, user)
  await page.goto('/app/phrases')

  await page.getByRole('button', { name: t('en', 'presenter.enter') }).click()
  const bar = page.getByRole('region', { name: t('en', 'presenter.title') })
  await expect(bar).toBeVisible()
  await expect(bar.getByText(t('en', 'presenter.stepIndicator', { current: 2, total: 5 }))).toBeVisible()
  await bar.getByRole('button', { name: t('en', 'presenter.next') }).click()
  await expect(page).toHaveURL(/\/app\/speak$/)
  await bar.getByRole('button', { name: t('en', 'presenter.prev') }).click()
  await expect(page).toHaveURL(/\/app\/phrases$/)

  await bar.getByRole('button', { name: t('en', 'presenter.exit') }).click()
  await expect(bar).toHaveCount(0)
  await page.keyboard.press('Alt+P')
  await expect(bar).toBeVisible()
})
