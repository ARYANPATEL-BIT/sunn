// End-to-end tests (web/e2e) against the real app: src/server.py serving the API and the built
// web app on one port, with GNANI_MOCK on so no test spends Gnani credits. `npm run e2e` builds
// the web app first; the server starts with an empty data folder of its own.
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from '@playwright/test'
import { wav } from './e2e/audio.js'

export const PORT = 7861
const ROOT = fileURLToPath(new URL('..', import.meta.url))
// The fake microphone plays this tone on a loop, so a recording is never silent.
const TONE = path.join(os.tmpdir(), 'sunn-e2e-tone.wav')
fs.writeFileSync(TONE, wav(2, 220, 48000))

export default defineConfig({
  testDir: 'e2e',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  retries: 0,
  workers: 4,
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${PORT}`,
    permissions: ['microphone'],
    // Still pages give steady timings; motion.spec.js covers both settings.
    reducedMotion: 'reduce',
    launchOptions: {
      args: [
        '--use-fake-ui-for-media-stream',
        '--use-fake-device-for-media-stream',
        `--use-file-for-fake-audio-capture=${TONE}`,
        '--autoplay-policy=no-user-gesture-required',
      ],
    },
  },
  projects: [
    { name: 'phone', use: { viewport: { width: 390, height: 844 } } },
    { name: 'desktop', use: { viewport: { width: 1440, height: 900 } } },
  ],
  webServer: {
    command: `uv run src/server.py --port ${PORT}`,
    cwd: ROOT,
    url: `http://localhost:${PORT}/health`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      GNANI_MOCK: '1',
      // No LLM calls and no reranker in the e2e, whatever .env says.
      LLM_ENABLED: '0',
      RERANKER_ENABLED: '0',
      TRUST_PROXY: '0',
      GOOGLE_CLIENT_ID: '',
      // Every e2e sign-up comes from this machine; the 5 an hour per IP is tests/test_signup.py's.
      SIGNUPS_PER_IP_PER_HOUR: '100000',
      DATA_DIR: fs.mkdtempSync(path.join(os.tmpdir(), 'sunn-e2e-data-')),
    },
  },
})
