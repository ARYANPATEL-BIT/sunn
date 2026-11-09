import {
  expect, expectNoLeaks, LANGS, markOnboarded, nativeName, openSpeak, phraseCard, QUICK_START, record, signUp, t, test, wav,
} from './helpers.js'

const other = (code) => (code === 'en' ? 'hi' : 'en')
const speakName = (lang, code) => t(lang, code === 'hi' ? 'settings.speakHindi' : 'settings.speakEnglish')

for (const lang of LANGS) {
  test.describe(`settings, ${lang}`, () => {
    test.use({ lang })

    test('own voice, both languages, text size, caregiver, delete account', async ({ page, watch }) => {
      const user = await signUp(page.request, { speaks: lang })
      await openSpeak(page.request, user)
      await markOnboarded(page, user)
      const patches = []
      page.on('request', (r) => r.method() === 'PATCH' && r.url().endsWith('/api/me') && patches.push(r.postDataJSON()))

      await page.goto('/app/settings')
      await expect(page.getByRole('heading', { level: 1, name: t(lang, 'settings.title') })).toBeVisible()
      await expectNoLeaks(page, lang)

      // --- own voice: upload with consent, preview, use it on Speak, remove it
      await expect(page.getByText(t(lang, 'settings.voiceStandard'))).toBeVisible()
      const upload = page.getByRole('button', { name: t(lang, 'settings.voiceUpload') })
      await expect(upload).toBeDisabled() // consent first
      await page.getByLabel(t(lang, 'settings.voiceFile')).setInputFiles({
        name: 'voice.wav', mimeType: 'audio/wav', buffer: wav(6, 180),
      })
      await page.getByRole('checkbox', { name: t(lang, 'settings.voiceConsent') }).check()
      const cloned = page.waitForResponse((r) => r.url().endsWith('/api/me/voice'))
      await upload.click()
      expect((await cloned).status()).toBe(200)
      await expect(page.getByText(t(lang, 'settings.voiceRecorded'))).toBeVisible()

      const ownVoice = page.locator('.settings-row', { hasText: t(lang, 'settings.useOwnVoiceLabel') }).getByRole('button')
      await expect(ownVoice).toHaveAttribute('aria-pressed', 'false')
      await ownVoice.click()
      await expect(ownVoice).toHaveAttribute('aria-pressed', 'true')
      expect(patches.at(-1)).toEqual({ use_own_voice: true })
      const preview = page.waitForResponse((r) => r.url().endsWith('/api/speak'))
      await page.getByRole('button', { name: t(lang, 'settings.testVoice') }).click()
      expect((await preview).status()).toBe(200)
      await expectNoLeaks(page, lang)

      await page.getByRole('link', { name: t(lang, 'tab.speak') }).click()
      await record(page, lang)
      const spoken = page.waitForResponse((r) => r.url().endsWith('/api/speak'))
      await page.locator('.candidate').first().click()
      expect((await spoken).status()).toBe(200) // the server speaks in the cloned voice while it is on
      await expect(page.getByText(t(lang, 'speak.played'))).toBeVisible()

      await page.getByRole('link', { name: t(lang, 'tab.settings') }).first().click()
      await page.getByRole('button', { name: t(lang, 'settings.deleteVoice') }).click()
      const forgotten = page.waitForResponse((r) => r.url().endsWith('/api/me/voice') && r.request().method() === 'DELETE')
      await page.getByRole('button', { name: t(lang, 'settings.deleteVoiceYes') }).click()
      expect((await forgotten).status()).toBe(200)
      await expect(page.getByText(t(lang, 'settings.voiceStandard'))).toBeVisible()
      await expect(page.getByLabel(t(lang, 'settings.voiceFile'))).toBeVisible()

      // --- the app's language is this device's only: no request to the server
      const appLanguage = page.getByRole('radiogroup', { name: t(lang, 'settings.languageLabel') })
      const sent = patches.length
      await appLanguage.getByRole('radio', { name: nativeName(other(lang)) }).click()
      await expect(page.locator('html')).toHaveAttribute('lang', other(lang))
      await expect(page.getByRole('heading', { level: 1, name: t(other(lang), 'settings.title') })).toBeVisible()
      await expectNoLeaks(page, other(lang), [user.name]) // the name is the user's, in their script
      await page.getByRole('radiogroup', { name: t(other(lang), 'settings.languageLabel') })
        .getByRole('radio', { name: nativeName(lang) }).click()
      await expect(page.locator('html')).toHaveAttribute('lang', lang)
      expect(patches.length).toBe(sent)
      expect(await page.evaluate(() => localStorage.getItem('sunn.lang'))).toBe(lang)

      // --- the language spoken is the account's: asked first, then PATCH /me and the new phrases
      const speaks = other(lang)
      await page.getByRole('radiogroup', { name: t(lang, 'settings.speakLanguageLabel') })
        .getByRole('radio', { name: speakName(lang, speaks) }).click()
      await expect(page.getByText(t(lang, 'settings.speakLanguageConfirm', { language: speakName(lang, speaks) }))).toBeVisible()
      await expect(page.getByText(t(lang, 'settings.speakLanguageWarning', { language: speakName(lang, speaks) }))).toBeVisible()
      await expectNoLeaks(page, lang)
      const seeded = page.waitForResponse((r) => r.url().endsWith('/api/me/phrases/default'))
      await page.getByRole('button', { name: t(lang, 'settings.speakLanguageYes', { language: speakName(lang, speaks) }) }).click()
      expect((await seeded).status()).toBe(200)
      expect(patches.at(-1)).toEqual({ language: speaks })
      await expect(page.getByRole('radiogroup', { name: t(lang, 'settings.speakLanguageLabel') })
        .getByRole('radio', { name: speakName(lang, speaks) })).toHaveAttribute('aria-checked', 'true')

      // The phrases recorded in the old language now need recording again.
      await page.getByRole('link', { name: t(lang, 'tab.phrases') }).click()
      await page.getByRole('searchbox').fill(QUICK_START[lang][0])
      const old = phraseCard(page, QUICK_START[lang][0])
      await expect(old.getByText(t(lang, 'phrases.rerecord'), { exact: true })).toBeVisible()
      await expectNoLeaks(page, lang)
      await page.getByRole('link', { name: t(lang, 'tab.speak') }).click()
      await expect(page.getByRole('heading', { name: t(lang, 'speak.none') })).toBeVisible()

      // --- text size
      await page.getByRole('link', { name: t(lang, 'tab.settings') }).first().click()
      const size = page.getByRole('radiogroup', { name: t(lang, 'settings.textSizeLabel') })
      await size.getByRole('radio', { name: t(lang, 'settings.textSizeLarge') }).click()
      await expect(page.locator('html')).toHaveClass(/large-text/)
      await expectNoLeaks(page, lang)
      await size.getByRole('radio', { name: t(lang, 'settings.textSizeDefault') }).click()
      await expect(page.locator('html')).not.toHaveClass(/large-text/)

      // --- caregiver: the number comes back ready for wa.me
      await page.getByLabel(t(lang, 'settings.caregiverNameLabel')).fill(lang === 'hi' ? 'राहुल' : 'Rahul')
      await page.getByLabel(t(lang, 'settings.caregiverPhoneLabel')).fill('+91 98765 43210')
      await page.getByRole('button', { name: t(lang, 'settings.saveCaregiver') }).click()
      await expect(page.getByRole('link', { name: t(lang, 'settings.openWhatsApp') })).toHaveAttribute('href', 'https://wa.me/919876543210')

      // --- delete the account: signed out, local state gone, back on the landing page
      await page.getByRole('button', { name: t(lang, 'settings.deleteAccount') }).click()
      await expect(page.getByText(t(lang, 'settings.deleteAccountWarning'))).toBeVisible()
      await expectNoLeaks(page, lang)
      const deleted = page.waitForResponse((r) => r.url().endsWith('/api/me') && r.request().method() === 'DELETE')
      await page.getByRole('button', { name: t(lang, 'settings.deleteAccountYes') }).click()
      expect((await deleted).status()).toBe(200)
      await expect(page).toHaveURL(/\/$/)
      await expect(page.getByRole('link', { name: t(lang, 'nav.signIn') })).toBeVisible()
      expect(await page.evaluate((id) => localStorage.getItem(`sunn.onboarded.${id}`), user.id)).toBeNull()
      expect((await page.request.get('/api/auth/me')).status()).toBe(401)
      watch.allow(401, '/api/auth/me')
      await page.goto('/app/settings')
      await expect(page).toHaveURL('/login?next=%2Fapp%2Fsettings')
    })
  })
}
