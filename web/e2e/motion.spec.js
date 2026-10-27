import { expect, markOnboarded, openSpeak, signUp, t, test } from './helpers.js'

// Counts the animation frames the page asks for; the background asks for about 30 a second
// while it moves, and none once it is still.
const COUNT_FRAMES = () => {
  const raf = window.requestAnimationFrame.bind(window)
  window.__frames = 0
  window.requestAnimationFrame = (callback) => {
    window.__frames++
    return raf(callback)
  }
}
async function framesInASecond(page) {
  const before = await page.evaluate(() => window.__frames)
  await page.waitForTimeout(1000)
  return (await page.evaluate(() => window.__frames)) - before
}
const running = (page) =>
  page.evaluate(() => document.getAnimations().filter((a) => a.playState === 'running').length)

test.describe('motion allowed', () => {
  test.use({ reducedMotion: 'no-preference' })

  test('the background moves and the sun breathes', async ({ page }) => {
    const user = await signUp(page.request)
    await openSpeak(page.request, user)
    await markOnboarded(page, user)
    await page.addInitScript(COUNT_FRAMES)
    await page.goto('/app/speak')
    await expect(page.getByRole('button', { name: t('en', 'sun.tap') })).toBeVisible()
    expect(await framesInASecond(page)).toBeGreaterThan(10)
    expect(await running(page)).toBeGreaterThan(0)
  })

  test("the app's own setting stops the motion at once, and starts it again", async ({ page }) => {
    const user = await signUp(page.request)
    await markOnboarded(page, user)
    await page.addInitScript(COUNT_FRAMES)
    await page.goto('/app/settings')
    expect(await framesInASecond(page)).toBeGreaterThan(10)

    const toggle = page.locator('.settings-row', { hasText: t('en', 'settings.motionLabel') }).getByRole('button')
    await toggle.click()
    await expect(page.locator('html')).toHaveClass(/reduced-motion/)
    await page.waitForTimeout(300) // let the last frame finish
    expect(await framesInASecond(page)).toBeLessThanOrEqual(1)
    expect(await running(page)).toBe(0)

    await toggle.click()
    await expect(page.locator('html')).not.toHaveClass(/reduced-motion/)
    expect(await framesInASecond(page)).toBeGreaterThan(10)
  })
})

test.describe('system reduced motion', () => {
  test.use({ reducedMotion: 'reduce' })

  test('nothing moves on the landing page or on speak', async ({ page, watch }) => {
    watch.allow(401, '/api/auth/me')
    await page.addInitScript(COUNT_FRAMES)
    await page.goto('/')
    await expect(page.locator('html')).toHaveClass(/reduced-motion/)
    expect(await framesInASecond(page)).toBeLessThanOrEqual(1)
    expect(await running(page)).toBe(0)
    // The example shows a finished example, paused, with the button to play it.
    await expect(page.getByRole('button', { name: t('en', 'example.play') })).toBeVisible()
    await expect(page.locator('.example')).toHaveAttribute('data-phase', 'said')

    const user = await signUp(page.request)
    await openSpeak(page.request, user)
    await markOnboarded(page, user)
    await page.goto('/app/speak')
    await expect(page.getByRole('button', { name: t('en', 'sun.tap') })).toBeVisible()
    expect(await framesInASecond(page)).toBeLessThanOrEqual(1)
    expect(await running(page)).toBe(0)
  })
})
