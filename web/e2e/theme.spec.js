import { expect, markOnboarded, refuseOnce, signUp, t, test } from './helpers.js'

// The theme is one value for the page: a /auth/me refresh, a device color change or a toggle
// mounting on another page never turns a chosen light or dark back into automatic.
const ICON = { light: 'sun', dark: 'moon', system: 'contrast' }
const toggle = (page) => page.locator('header').getByRole('button', { name: /^Appearance:/ })
const settingsChoice = (page, theme) =>
  page.getByRole('radiogroup', { name: t('en', 'settings.themeLabel') }).getByRole('radio', { name: t('en', `theme.${theme}`) })

async function expectChoice(page, theme, shown = theme) {
  await expect(toggle(page)).toHaveAttribute('aria-label', t('en', 'theme.toggle', { theme: t('en', `theme.${theme}`) }))
  await expect(toggle(page).locator('svg')).toHaveAttribute('data-icon', ICON[theme])
  await expect(page.locator('html')).toHaveAttribute('data-theme', shown)
}

// The device flips to the other scheme and back.
async function flipDevice(page) {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.emulateMedia({ colorScheme: 'light' })
}

for (const storage of ['saved', 'blocked']) {
  for (const theme of ['dark', 'light']) {
    test(`${theme} stays ${theme} through a session refresh, a device change and remounts (storage ${storage})`, async ({
      page,
      watch,
    }) => {
      const user = await signUp(page.request)
      await markOnboarded(page, user)
      if (storage === 'blocked') {
        // A private window or webview: every storage call throws, after the fixtures ran.
        await page.addInitScript(() => {
          for (const m of ['getItem', 'setItem']) Storage.prototype[m] = () => { throw new DOMException('blocked', 'SecurityError') }
        })
      }
      await page.emulateMedia({ colorScheme: 'light' })
      await refuseOnce(page, watch, '/api/auth/me', 503, { code: 'server_error' })
      await page.goto('/')

      // Pick it in the landing nav: from automatic on a light device, dark comes first, then light.
      await toggle(page).click()
      if (theme === 'light') await toggle(page).click()
      await expectChoice(page, theme)
      await flipDevice(page)
      await expectChoice(page, theme)

      // Into the app, where the session check failed: Try again runs /auth/me again and mounts
      // the app's own header and Settings.
      await page.evaluate(() => {
        history.pushState({}, '', '/app/settings')
        dispatchEvent(new PopStateEvent('popstate'))
      })
      await page.getByRole('button', { name: t('en', 'error.retry') }).click()
      await expect(page.getByRole('heading', { level: 1, name: t('en', 'settings.title') })).toBeVisible()
      await expectChoice(page, theme)
      await expect(settingsChoice(page, theme)).toHaveAttribute('aria-checked', 'true')

      // Home and back: both headers mount again.
      await page.getByRole('link', { name: t('en', 'nav.home') }).first().click()
      await expectChoice(page, theme)
      await page.getByRole('link', { name: t('en', 'nav.openApp') }).first().click()
      await page.getByRole('link', { name: t('en', 'tab.settings') }).first().click()
      await expectChoice(page, theme)

      // The nav toggle and Settings show the same choice, whichever changes it.
      await toggle(page).click()
      const next = theme === 'dark' ? 'light' : 'system'
      await expectChoice(page, next, next === 'system' ? 'light' : next)
      await expect(settingsChoice(page, next)).toHaveAttribute('aria-checked', 'true')
      await settingsChoice(page, theme).click()
      await expectChoice(page, theme)

      if (storage === 'saved') {
        await page.reload()
        await expectChoice(page, theme)
      }
    })
  }
}

test('automatic follows the device, in both toggles', async ({ page }) => {
  const user = await signUp(page.request)
  await markOnboarded(page, user)
  await page.emulateMedia({ colorScheme: 'light' })
  await page.goto('/app/settings')
  await settingsChoice(page, 'dark').click()
  await settingsChoice(page, 'system').click()
  await expectChoice(page, 'system', 'light')

  await page.emulateMedia({ colorScheme: 'dark' })
  await expectChoice(page, 'system', 'dark')
  await expect(settingsChoice(page, 'system')).toHaveAttribute('aria-checked', 'true')
  await page.emulateMedia({ colorScheme: 'light' })
  await expectChoice(page, 'system', 'light')
  expect(await page.evaluate(() => localStorage.getItem('sunn.theme'))).toBe('system')
})
