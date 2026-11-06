import { expect, markOnboarded, openSpeak, signUp, t, test } from './helpers.js'

// Counts the animation frames the page asks for. Nothing asks for any at rest; while recording,
// the recorder asks for one a frame to measure the voice, and the readout's blob one to draw it.
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
// How loud the readout's blob thinks the voice is (its --level, 0..1), which sizes its glow,
// and the blob's outline, which wobbles with the voice unless motion is reduced.
const level = (blob) => blob.evaluate((el) => parseFloat(el.style.getPropertyValue('--level')) || 0)
const outline = (blob) => blob.locator('path').getAttribute('d')

test.describe('motion allowed', () => {
  test.use({ reducedMotion: 'no-preference' })

  test('the landing example plays, and the blob follows the voice', async ({ page, watch }) => {
    watch.allow(401, '/api/auth/me')
    await page.goto('/')
    const example = page.locator('.example')
    await expect(page.getByRole('button', { name: t('en', 'example.pause') })).toBeVisible()
    for (const phase of ['heard', 'said', 'wave']) await expect(example).toHaveAttribute('data-phase', phase)

    const user = await signUp(page.request)
    await openSpeak(page.request, user)
    await markOnboarded(page, user)
    await page.goto('/app/speak')
    const button = page.locator('button.record')
    const blob = page.locator('.speak .blob')
    const still = await outline(blob)
    await button.click()
    await expect(button).toHaveClass(/recording/)
    await expect(blob).toHaveAttribute('data-state', 'listening')
    await expect.poll(() => level(blob)).toBeGreaterThan(0.2) // the fake microphone's tone
    await expect.poll(() => outline(blob)).not.toBe(still) // and the shape wobbles
    await button.click()
    await expect(button).not.toHaveClass(/recording/)
    expect(await level(blob)).toBe(0)
  })

  test("the app's own setting stops the motion at once, and starts it again", async ({ page }) => {
    const user = await signUp(page.request)
    await openSpeak(page.request, user)
    await markOnboarded(page, user)
    await page.goto('/app/settings')

    const toggle = page.locator('.settings-row', { hasText: t('en', 'settings.motionLabel') }).getByRole('button')
    await toggle.click()
    await expect(page.locator('html')).toHaveClass(/reduced-motion/)
    expect(await running(page)).toBe(0) // the switch doesn't slide, the saved note doesn't rise

    // Without a reload: while recording the blob keeps its circle (it only scales with the voice).
    const speak = page.getByRole('link', { name: t('en', 'tab.speak') })
    const button = page.locator('button.record')
    const blob = page.locator('.speak .blob')
    await speak.click()
    const circle = await outline(blob)
    await button.click()
    await expect(button).toHaveClass(/recording/)
    await expect.poll(() => level(blob)).toBeGreaterThan(0.2)
    await page.waitForTimeout(600)
    expect(await outline(blob)).toBe(circle)
    expect(await running(page)).toBe(0)
    await button.click()
    await expect(button).not.toHaveClass(/recording/)

    await page.getByRole('link', { name: t('en', 'tab.settings') }).first().click()
    await toggle.click()
    await expect(page.locator('html')).not.toHaveClass(/reduced-motion/)
    await speak.click()
    await button.click()
    await expect(button).toHaveClass(/recording/)
    await expect.poll(() => level(blob)).toBeGreaterThan(0.2)
    await expect.poll(() => outline(blob)).not.toBe(circle)
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
