import { expect, expectNoLeaks, nativeName, t, test } from './helpers.js'

// The language picker in the landing nav: a list on phones (bottom sheet) and desktops (menu).
const picker = (page, ui) => page.locator('.site-nav').getByRole('button', { name: t(ui, 'lang.label') })

async function choose(page, ui, code) {
  await picker(page, ui).click()
  const list = page.getByRole('listbox', { name: t(ui, 'lang.label') })
  await expect(list.getByRole('option')).toHaveCount(10)
  await list.getByRole('option', { name: nativeName(code) }).click()
  await expect(page.locator('html')).toHaveAttribute('lang', code)
  await expect(list).toHaveCount(0)
}

async function expectLanguage(page, code) {
  await expect(page.locator('html')).toHaveAttribute('lang', code)
  await expect(picker(page, code)).toContainText(nativeName(code))
  await expect(page.locator('.display-other')).toHaveText(t(code, 'hero.headline'))
  // Only this script's font is fetched.
  await expect(page.locator(`link[data-font="${code}"]`)).toHaveCount(1)
  expect(await page.locator('link[data-font]').count()).toBe(1)
  await expectNoLeaks(page, code)
}

test('switch to Tamil and Bengali from the landing nav, and the choice is kept', async ({ page, watch }) => {
  watch.allow(401, '/api/auth/me') // signed out
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')

  await choose(page, 'en', 'ta')
  await expectLanguage(page, 'ta')
  await page.reload()
  await expectLanguage(page, 'ta')

  await choose(page, 'ta', 'bn')
  await page.reload()
  await expectLanguage(page, 'bn')
  expect(await page.evaluate(() => localStorage.getItem('sunn.lang'))).toBe('bn')
})

test('the picker works from the keyboard', async ({ page, watch }) => {
  watch.allow(401, '/api/auth/me')
  await page.goto('/')
  const button = picker(page, 'en')
  await button.focus()
  await page.keyboard.press('Enter')
  const selected = page.getByRole('option', { name: nativeName('en') })
  await expect(selected).toBeFocused()
  await expect(selected).toHaveAttribute('aria-selected', 'true')

  await page.keyboard.press('Escape')
  await expect(page.getByRole('listbox')).toHaveCount(0)
  await expect(button).toBeFocused()

  await page.keyboard.press('Enter')
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('option', { name: nativeName('hi') })).toBeFocused()
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  await expect(page.locator('html')).toHaveAttribute('lang', 'ta')
  await expect(picker(page, 'ta')).toBeFocused()
})

test('a first visit takes the browser language when it is one of the ten', async ({ browser }) => {
  // A fresh page without the fixture's saved language, in a Malayalam browser.
  for (const [locale, code] of [['ml-IN', 'ml'], ['fr-FR', 'en']]) {
    const context = await browser.newContext({ locale, baseURL: test.info().project.use.baseURL })
    const page = await context.newPage()
    await page.goto('/')
    await expect(page.locator('html')).toHaveAttribute('lang', code)
    await context.close()
  }
})
