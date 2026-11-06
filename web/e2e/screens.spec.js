// Screenshots of every screen and state, in both languages and both themes, at phone width
// (the phone project, 390) and desktop width (the desktop project, 1440), for docs/screenshots.
// Run with `npx playwright test screens`; they are looked at by a person.
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import {
  enroll, expect, LANGS, markOnboarded, openPhrase, openSpeak, QUICK_START, recognizeAndConfirm, record, refuseOnce,
  signUp, t, test, wav,
} from './helpers.js'

const ROOT = fileURLToPath(new URL('../../docs/screenshots/', import.meta.url))

for (const theme of ['light', 'dark']) {
  for (const lang of LANGS) {
    test.describe(`screens, ${theme}, ${lang}`, () => {
      // The theme is left on automatic and follows the (emulated) device, as it does by default.
      test.use({ lang, colorScheme: theme })

      test('every screen and state', async ({ page, watch }, info) => {
        test.setTimeout(300_000)
        watch.allow(401, '/api/auth/me')
        watch.allow(401, '/api/auth/login')
        const out = `${ROOT}${page.viewportSize().width}-${theme}/`
        fs.mkdirSync(out, { recursive: true })
        let n = 0
        // A tall page is shot with the window as tall as the page, so the tab bar is where it
        // really is (a stitched full-page shot leaves it in the middle). An open sheet is shot as
        // the screen shows it.
        const shot = async (name, { sheet = false } = {}) => {
          await page.mouse.move(0, 0) // no hover left over from the last click
          await page.evaluate(() => document.fonts.load('600 16px "Noto Sans Devanagari"', 'हिं'))
          await page.waitForTimeout(150) // fonts and the last layout settle
          n++
          const options = { path: `${out}${lang}-${String(n).padStart(2, '0')}-${name}.jpg`, type: 'jpeg', quality: 72 }
          const viewport = page.viewportSize()
          const height = await page.evaluate(() => document.documentElement.scrollHeight)
          if (sheet || height <= viewport.height) return page.screenshot(options)
          await page.setViewportSize({ width: viewport.width, height })
          await page.waitForTimeout(100)
          await page.screenshot(options)
          await page.setViewportSize(viewport)
        }
        const water = QUICK_START[lang][2]

        // --- signed out
        await page.goto('/')
        await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
        await page.evaluate(() => document.fonts.ready)
        await shot('landing')
        await page.goto('/login')
        await shot('login')
        // Its own address per run: five wrong tries on one address lock it (auth.spec.js).
        await page.getByLabel(t(lang, 'auth.email')).fill(`nobody-${lang}-${theme}-${info.project.name}@example.com`)
        await page.getByLabel(t(lang, 'auth.password'), { exact: true }).fill('wrong-password')
        await page.getByRole('button', { name: t(lang, 'login.submit') }).click()
        await expect(page.getByRole('alert')).toBeVisible()
        await shot('login-error')
        await page.goto('/signup')
        await expect(page.getByLabel(t(lang, 'signup.inviteCode'))).toBeVisible()
        await shot('signup')
        await page.getByLabel(t(lang, 'signup.name')).fill(lang === 'hi' ? 'आशा' : 'Asha')
        await page.getByLabel(t(lang, 'auth.email')).fill(`shots-${lang}-${theme}-${info.project.name}-${Date.now()}@example.com`)
        await page.getByLabel(t(lang, 'auth.password'), { exact: true }).fill('e2e-password-1')
        await page.getByLabel(t(lang, 'signup.inviteCode')).fill('wrong')
        await refuseOnce(page, watch, '/api/auth/signup', 403, { error: 'invite_required' })
        await page.getByRole('checkbox', { name: t(lang, 'signup.consent') }).check()
        await page.getByRole('button', { name: t(lang, 'signup.submit') }).click()
        await expect(page.getByText(t(lang, 'error.invite_required'))).toBeVisible()
        await shot('signup-error')

        // --- a new account: the welcome guide, Teach, Speak still closed, empty progress
        const user = await signUp(page.request, { speaks: lang })
        await page.goto('/app/onboarding')
        for (let step = 1; step <= 4; step++) {
          await expect(page.getByText(t(lang, 'onboarding.stepProgress', { current: step, total: 4 })).first()).toBeVisible()
          await shot(`onboarding-${step}`)
          if (step < 4) await page.getByRole('button', { name: t(lang, 'onboarding.next') }).click()
        }
        await page.goto('/app/enroll')
        await expect(page.getByText(t(lang, 'enroll.quickStart'))).toBeVisible()
        await shot('teach')
        await record(page, lang)
        await expect(page.getByRole('button', { name: t(lang, 'enroll.save') })).toBeVisible()
        await shot('teach-recorded')
        await page.goto('/app/speak')
        await expect(page.getByRole('heading', { name: t(lang, 'speak.none') })).toBeVisible()
        await shot('speak-closed')
        await page.goto('/app/progress')
        await expect(page.getByRole('heading', { name: t(lang, 'progress.nothing') })).toBeVisible()
        await shot('progress-empty')

        // --- the same account, ready: Speak, the library, progress with data, settings
        await openSpeak(page.request, user)
        await markOnboarded(page, user)
        const waterPhrase = user.phrases.find((p) => p.text === water)
        await enroll(page.request, waterPhrase.id, 1, 'simulated')
        for (let i = 0; i < 3; i++) await recognizeAndConfirm(page.request, waterPhrase.id)
        await page.goto('/app/enroll')
        await expect(page.getByText(t(lang, 'enroll.quickDone'))).toBeVisible()
        await shot('teach-quick-start-done')
        await page.goto('/app/speak')
        await expect(page.getByRole('button', { name: t(lang, 'sun.tap') })).toBeVisible()
        await shot('speak')
        await page.getByRole('radio', { name: t(lang, 'speak.context_hospital') }).click()
        await page.getByRole('button', { name: t(lang, 'sun.tap') }).click()
        const stop = page.getByRole('button', { name: new RegExp(t(lang, 'sun.stop')) })
        await expect(stop).toBeVisible()
        await page.waitForTimeout(1200)
        await shot('speak-recording')
        await stop.click()
        await expect(page.locator('.candidate').first()).toBeVisible()
        await shot('speak-candidates')
        await page.locator('.candidate').first().click()
        await expect(page.getByText(t(lang, 'speak.played'))).toBeVisible()
        await shot('speak-played')
        await page.getByRole('button', { name: t(lang, 'speak.noneOfThese') }).click()
        await page.getByLabel(t(lang, 'speak.typeLabel')).fill(lang === 'hi' ? 'खिड़की खोल दो' : 'Please open the window')
        await shot('speak-type-it', { sheet: true })

        await page.goto('/app/phrases')
        await expect(page.getByText(t(lang, 'phrases.total', { count: 51 }))).toBeVisible()
        await shot('phrases')
        await page.getByRole('searchbox').fill(water)
        await openPhrase(page, water)
        await shot('phrases-details', { sheet: true })
        await page.getByRole('button', { name: `${t(lang, 'phrases.edit')}: ${water}` }).click()
        await shot('phrases-edit', { sheet: true })
        await page.getByRole('button', { name: t(lang, 'phrases.cancel') }).click()
        await page.getByRole('button', { name: `${t(lang, 'phrases.delete')}: ${water}` }).click()
        await shot('phrases-delete', { sheet: true })
        await page.getByRole('button', { name: t(lang, 'phrases.deleteNo') }).click()
        await page.getByRole('button', { name: t(lang, 'sheet.close') }).click()
        await page.getByRole('button', { name: t(lang, 'phrases.add') }).click()
        await shot('phrases-add', { sheet: true })

        await page.goto('/app/progress')
        await expect(page.getByRole('img', { name: t(lang, 'progress.weeklyDesc') })).toBeVisible()
        await shot('progress')
        await page.getByRole('button', { name: t(lang, 'progress.weeklyTableToggle') }).click()
        await shot('progress-table')

        await page.goto('/app/settings')
        await expect(page.getByRole('heading', { level: 1, name: t(lang, 'settings.title') })).toBeVisible()
        await shot('settings')
        await page.getByLabel(t(lang, 'settings.voiceFile')).setInputFiles({ name: 'voice.wav', mimeType: 'audio/wav', buffer: wav(6, 180) })
        await page.getByRole('checkbox', { name: t(lang, 'settings.voiceConsent') }).check()
        await page.getByRole('button', { name: t(lang, 'settings.voiceUpload') }).click()
        await expect(page.getByText(t(lang, 'settings.voiceRecorded'))).toBeVisible()
        await shot('settings-own-voice')
        const other = lang === 'en' ? 'hi' : 'en'
        await page.getByRole('radiogroup', { name: t(lang, 'settings.speakLanguageLabel') })
          .getByRole('radio', { name: t(lang, other === 'hi' ? 'settings.speakHindi' : 'settings.speakEnglish') }).click()
        await shot('settings-speak-language', { sheet: true })
        await page.getByRole('button', { name: t(lang, 'settings.cancel') }).click()
        await page.getByRole('button', { name: t(lang, 'settings.deleteAccount') }).click()
        await shot('settings-delete-account', { sheet: true })
        await page.getByRole('button', { name: t(lang, 'settings.deleteAccountNo') }).click()
        await page.getByRole('radiogroup', { name: t(lang, 'settings.textSizeLabel') })
          .getByRole('radio', { name: t(lang, 'settings.textSizeLarge') }).click()
        await page.goto('/app/speak')
        await shot('speak-large-text')
      })
    })
  }
}
