import { expect, markOnboarded, openSpeak, signUp, t, test } from './helpers.js'

// Presses Tab until `target` has focus, as a keyboard user would.
async function tabTo(page, target, max = 80) {
  for (let i = 0; i < max; i++) {
    if (await target.evaluate((el) => el === document.activeElement)) return
    await page.keyboard.press('Tab')
  }
  throw new Error(`Tab never reached ${target}`)
}

// Tabs through the whole screen, once round. Each stop must show a focus ring: on the element,
// or on what draws it (the label of a styled radio or checkbox, a field's wrapper, the pill
// that stands in for a hidden file input).
async function tabStopsWithoutFocusRing(page, max = 150) {
  const missing = []
  let stops = 0
  for (let i = 0; i < max; i++) {
    await page.keyboard.press('Tab')
    const stop = await page.evaluate(() => {
      const el = document.activeElement
      if (!el || el === document.body) return { skip: true }
      if (el.dataset.e2eVisited) return { done: true }
      el.dataset.e2eVisited = '1'
      const ring = (node) => {
        if (!node) return false
        const s = getComputedStyle(node)
        return (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none'
      }
      const visible = [el, el.parentElement, el.closest('label'), el.nextElementSibling].some(ring)
      return { visible, name: el.getAttribute('aria-label') || el.textContent.trim().slice(0, 50) || el.outerHTML.slice(0, 60) }
    })
    if (stop.done) break
    if (stop.skip) continue
    stops++
    if (!stop.visible) missing.push(stop.name)
  }
  return { stops, missing }
}

const SCREENS = ['/app/speak', '/app/enroll', '/app/phrases', '/app/progress', '/app/settings', '/app/onboarding']

test.describe('keyboard only', () => {
  test('every stop on every screen shows where focus is', async ({ page, watch }) => {
    watch.allow(401, '/api/auth/me')
    for (const path of ['/', '/login', '/signup']) {
      await page.goto(path)
      const { stops, missing } = await tabStopsWithoutFocusRing(page)
      expect(stops, path).toBeGreaterThan(2)
      expect(missing, `no focus ring on ${path}`).toEqual([])
    }
    const user = await signUp(page.request)
    await openSpeak(page.request, user)
    await markOnboarded(page, user)
    for (const path of SCREENS) {
      await page.goto(path)
      await expect(page.getByRole('navigation', { name: t('en', 'app.nav') })).toBeVisible()
      const { stops, missing } = await tabStopsWithoutFocusRing(page)
      expect(stops, path).toBeGreaterThan(5)
      expect(missing, `no focus ring on ${path}`).toEqual([])
    }
  })

  test('sign in, speak, pick a phrase and add one, with the keyboard alone', async ({ page, request, watch }) => {
    watch.allow(401, '/api/auth/me')
    const user = await signUp(request)
    await openSpeak(request, user)
    await markOnboarded(page, user)

    await page.goto('/login')
    await tabTo(page, page.getByLabel(t('en', 'auth.email')))
    await page.keyboard.type(user.email)
    await tabTo(page, page.getByLabel(t('en', 'auth.password'), { exact: true }))
    await page.keyboard.type(user.password)
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/app\/speak$/)

    const sun = page.locator('button.sun')
    await tabTo(page, sun)
    await page.keyboard.press('Enter')
    await expect(sun).toHaveClass(/recording/)
    await page.waitForTimeout(1500)
    await page.keyboard.press('Enter')
    const first = page.locator('.candidate').first()
    await expect(first).toBeVisible()
    await tabTo(page, first)
    const spoken = page.waitForResponse((r) => r.url().endsWith('/api/speak'))
    await page.keyboard.press('Enter')
    expect((await spoken).status()).toBe(200)

    await page.goto('/app/phrases')
    await tabTo(page, page.getByRole('button', { name: t('en', 'phrases.add') }))
    await page.keyboard.press('Enter')
    await expect(page.getByLabel(t('en', 'phrases.textLabel'), { exact: true })).toBeFocused()
    await page.keyboard.type('Bring my shawl')
    const added = page.waitForResponse((r) => r.url().endsWith('/api/me/phrases') && r.request().method() === 'POST')
    await page.keyboard.press('Enter')
    expect((await added).status()).toBe(200)
    await expect(page.getByText(t('en', 'phrases.addedSuccess'))).toBeVisible()
  })

  test('Escape leaves the welcome guide', async ({ page }) => {
    const user = await signUp(page.request)
    await page.goto('/app/onboarding')
    await expect(page.getByText(t('en', 'onboarding.stepProgress', { current: 1, total: 4 })).first()).toBeVisible()
    // The guide listens for Escape from an effect, just after its first paint: press until it hears.
    await expect(async () => {
      await page.keyboard.press('Escape')
      await expect(page).toHaveURL(/\/app\/speak$/, { timeout: 1000 })
    }).toPass()
    expect(await page.evaluate((id) => localStorage.getItem(`sunn.onboarded.${id}`), user.id)).toBe('true')
  })
})
