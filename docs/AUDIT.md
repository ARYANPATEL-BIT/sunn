# Final audit before submission

Branch `final-fix_audit`, from `main` at `db382fd` (2026-10-28). Three jobs: wire every screen
to the real backend, find and fix what was broken, and report. No new features, except two you
asked for: the quick start on Teach, and own-voice upload in Settings (its backend existed).
Every automated run used `GNANI_MOCK=1`, except the one real check (section 6).

## 0. State at the start

- `main` had six merges since the previous tip (#20 to #25: the deploy script, presenter mode,
  demo and submission readiness, deployment safety, the final submission package): 28 files,
  including the presenter bar, the invite code field, `scripts/deploy_space.py` and new docs.
- No `TODO`, `FIXME` or `TODO(v2)` left in `src/` or `web/src/`. One stale comment ("Backend
  language stub is non-blocking", `web/src/Settings.jsx`) hid a real bug (section 8). No mocks
  or stubs in the code; `docs/API.md` already says every route is real.
- Dead code: 20 of the 45 exports in `web/src/api.js` were unused (aliases, the building-block
  and usage clients, `deleteSample`): removed. Unused imports and variables in
  `web/src/Onboarding.jsx`: removed with the fix to that file (section 8).
- `uv run pytest`: 102 passed, 1 failed. The deploy dry run test failed because it inherited
  conftest's fake `GNANI_API_KEY` ("test-key") and then found that value in conftest.py itself.

## 1. Gnani mock mode

`GNANI_MOCK=1` answers every Gnani call locally (`src/gnani_mock.py`):

- Prisma: a transcript from `src/gnani_mock.json`, by the sha256 of the 16 kHz wav the server
  stores, else a default per language ("पानी चाहिए", "I need water"); `""` means no speech.
- Timbre: 0.5 s of silence. Voice cloning: a made-up embedding.
- Nothing is cached or counted in `api_calls`, so mock answers never mix with real ones, and
  `gnani.post` refuses to send anything while it is on.
- A banner of `!` lines on stderr and a `gnani_mock_on` warning in the log at startup.
- It is impossible in production: with `TRUST_PROXY` also set, importing the API raises and the
  server doesn't start (`tests/test_mock.py` starts a real process both ways; checked on the
  Docker image too). `scripts/evaluate.py` refuses to run with it, so no results file can come
  from made-up transcripts.

## 2. Wiring map

### Every backend endpoint, and who calls it

| Endpoint | Screen | Component | Status |
| - | - | - | - |
| `GET /config` | Sign up | `SignupPage` (AuthPages.jsx) | connected: the invite field shows when `invite_required` |
| `POST /auth/signup` | Sign up | `SignupPage` | connected; sends `invite_code`, the spoken language and consent |
| `POST /auth/login` | Sign in | `LoginPage` | connected |
| `POST /auth/logout` | app header | `AppShell` via `auth.jsx` | connected; **was** racing to `/login?next=…`, now lands on `/` |
| `GET /auth/me` | every page load | `AuthProvider` (auth.jsx) | connected |
| `PATCH /me` | Settings | `Settings.jsx` | **was called wrong**: the app-language toggle in Settings and the language cards in the welcome guide sent `{language}`, silently changing the spoken language. Both fixed; only Settings' own spoken-language control sends it now, after a warning |
| `DELETE /me` | Settings, Progress | `Settings.jsx`, `DeleteAccount` (Progress.jsx) via `auth.jsx` | connected; now also clears this browser's state for the account |
| `POST /me/voice` | Settings | `Settings.jsx` | **was not called**: no upload existed (the button sent users to Teach). Connected |
| `DELETE /me/voice` | Settings | `Settings.jsx` | connected |
| `GET /me/phrases` | Teach, Speak, Phrases, Progress, Welcome guide, Landing | Enroll, Speak, Phrases, Progress, Onboarding, Landing | connected; Teach, Speak, Phrases and Landing now decide from `sample_count` |
| `POST /me/phrases/default` | Sign up, Teach, Phrases, Welcome guide, Settings | AuthPages, Enroll, Phrases, Onboarding, Settings | connected; Settings now calls it after a spoken-language change, as docs/API.md says |
| `POST /me/phrases` | Phrases | `Phrases.jsx` | connected |
| `PATCH /me/phrases/{id}` | Phrases | `Phrases.jsx` | connected (text, places, urgent) |
| `DELETE /me/phrases/{id}` | Phrases | `Phrases.jsx` | connected, after a confirm |
| `DELETE /me/samples/{id}` | none | none | not called: no screen deletes a single recording |
| `POST /me/enroll` | Teach | `Enroll.jsx` | connected |
| `POST /me/recognize` | Speak | `Speak.jsx` | **was called wrong**: the default "Any" chip sent `context=any`, which the API refuses (422), so recognition failed until another chip was picked. Fixed: Any sends no context |
| `POST /me/confirm` | Speak | `Speak.jsx` | connected: `phrase_id`, a composed candidate's ids, or `new_text` from "None of these" |
| `POST /speak` | Speak, Phrases, Progress, Settings | Speak, Phrases (Listen), Progress (top phrases), Settings (Test voice) | connected; the server picks the cloned voice when it is on |
| `GET /me/stats` | Progress | `Progress.jsx` | connected; the screen **crashed** whenever a recognition had been confirmed (fixed) |
| `GET/POST/DELETE /me/slot-words`, `POST …/enroll` | none | none | not called: no building-block screens (README says so) |
| `GET/POST/DELETE /me/templates`, `POST …/enroll` | none | none | not called, as above |
| `GET /me/usage` | none | none | not called: owner-only, no screen |
| `GET /health`, `GET /api/health` | none | none | for Docker and Spaces probes |

### Every control, and what it calls

| Screen | Control | Calls | Works |
| - | - | - | - |
| all signed-out pages | EN / हिं | nothing (localStorage `sunn.lang`) | yes |
| Landing | Sign in / Open app | `/login` or `/app/speak` | yes |
| Landing | Start speaking (hero, closing) | `/login?next=/app/speak`; signed in: `GET /me/phrases`, then Teach until the quick start is done, else Speak | yes |
| Landing | How it works, Who it's for, Privacy links | page anchors | yes |
| Landing | example pause / play, FAQ questions | nothing | yes |
| Sign in | email, password, show / hide, Sign in | `POST /auth/login` | yes; wrong password and lockout worded |
| Sign up | name, email, invite code, password, show / hide, language you speak, consent, Create account | `GET /config`, `POST /auth/signup`, `POST /me/phrases/default` | yes; invite and lockout errors worded |
| app header | Sunn, Demo, EN / हिं, Settings, Log out | `/`; presenter bar; nothing; `/app/settings`; `POST /auth/logout` | yes |
| app | bottom tabs | navigation | yes |
| presenter bar | steps, previous, next, restart, collapse, close, Alt+P | navigation only | yes |
| Welcome guide | Skip setup, Continue, Back, Escape, Go to Speak | navigation, local flag | yes |
| Welcome guide | language cards | nothing (localStorage `sunn.lang`) | yes (fixed: they also sent `PATCH /me {language}`) |
| Welcome guide | Teach phrases now, Add everyday phrases, Open phrase library | `/app/enroll`; `POST /me/phrases/default`; `/app/phrases` | yes |
| Teach | sun, Play back, Save, Record again | `POST /me/enroll` (Save) | yes |
| Teach | Speak (after the quick start), Add everyday phrases, Try again | `/app/speak`; `POST /me/phrases/default`; `GET /me/phrases` | yes |
| Speak | Any / Home / Hospital / Market | sent with every `POST /me/recognize` (Any sends none) | yes (fixed) |
| Speak | sun | `POST /me/recognize` | yes |
| Speak | a candidate | `POST /me/confirm` and `POST /speak`, then plays | yes |
| Speak | None of these, Say it, Cancel, Stop audio, Try again | `POST /me/confirm {new_text}`, `POST /speak` | yes |
| Speak | Record phrases (closed until the quick start) | `/app/enroll` | yes |
| Phrases | Add phrase, Save phrase | `POST /me/phrases`, then `PATCH` for places or urgent | yes |
| Phrases | search, filter chips, Clear search | nothing | yes |
| Phrases | Listen, Edit, urgent box, Delete, Keep / Delete phrase | `POST /speak`; `PATCH /me/phrases/{id}`; `DELETE /me/phrases/{id}` | yes |
| Phrases | Add everyday phrases, Teach phrases (empty library) | `POST /me/phrases/default`; `/app/enroll` | yes |
| Progress | Show table / chart, Listen, quick links | nothing; `POST /speak`; navigation | yes (the table crashed before) |
| Progress | Delete my account and recordings | `DELETE /me` | yes |
| Settings | app language | nothing (localStorage) | yes (fixed) |
| Settings | language you speak, then its confirm | `PATCH /me {language}`, `POST /me/phrases/default` | yes (new control) |
| Settings | text size, reduced motion, focus outlines | nothing (localStorage) | yes |
| Settings | Choose a recording, consent, Add voice | `POST /me/voice` | yes (new) |
| Settings | Speak in my own voice, Test voice output | `PATCH /me {use_own_voice}`, `POST /speak` | yes |
| Settings | Delete cloned voice, then confirm | `DELETE /me/voice` | yes |
| Settings | caregiver name and phone, Save caregiver contact | `PATCH /me` | yes |
| Settings | Open WhatsApp contact | `https://wa.me/<digits>` | yes |
| Settings | Welcome guide | `/app/onboarding` | yes |
| Settings | Delete account and data, then confirm | `DELETE /me`, then the landing page | yes (fixed) |

Not built, so not wired or tested (your decision on 2026-10-28): an SOS button, a show-to-listener
mode, a bottom sheet, a building-blocks view or count, and onboarding steps for microphone
permission, caregiver and a 10-phrase quick start. Instead, Teach puts the 10 most important
default phrases first ("Record these 10 first. You can start speaking after that."), and Speak
opens once each of those has 3 recordings in the language spoken now (`web/src/quickstart.js`).
Speak shows a "record your first phrases" screen until then; the tab itself stays clickable.

## 3. End-to-end tests

`web/e2e`, Playwright against `src/server.py` in mock mode on port 7861 with an invite code and
an empty data folder, in Chromium at 390 x 844 and 1440 x 900, with a fake microphone that
plays a tone. `cd web; npm run e2e` builds the app and runs them.

| Spec | Covers |
| - | - |
| `auth.spec.js` | landing, Start speaking, sign in, back to Speak; every `/app` route sends to `/login?next=…`; wrong password and lockout wording; one real wrong invite code per run |
| `journey.spec.js` | sign-up with an invite code (wrong code, lockout wording, right code), the welcome guide, Teach with the quick start (record, play back, save), Speak closed then open, a context chip sent and Any sent as none, a candidate confirmed and played (real `audio/wav`, `playing` event), "None of these", the new phrase in the library |
| `phrases.spec.js` | edit text, mark urgent, delete with a confirm (and Keep), the "Simulated speech" label |
| `settings.spec.js` | own voice: upload with consent, toggle, preview, Speak in the cloned voice, remove; app language (no request sent); spoken language (confirm, `PATCH`, new phrases, "Record again" on the old ones, Speak closes); text size; caregiver and its wa.me link; account deletion (signed out, local flag gone, `/auth/me` 401, landing page) |
| `progress.spec.js` | the empty state of a new account, then counts, first-suggestion match, top phrases, the chart and the 8-week table |
| `keyboard.spec.js` | every Tab stop on 9 screens shows a focus ring; sign in, record, pick a phrase and add one with the keyboard alone; Escape leaves the welcome guide |
| `onboarding.spec.js` | the guide's language cards send no request and leave the spoken language alone; its last step says "ready" only once Speak is open |
| `motion.spec.js` | with motion: the background animates and the sun breathes; with system reduced motion nothing moves and the example is paused; the app's own setting stops and restarts motion without a reload |
| `presenter.spec.js` | the presenter bar opens, steps through screens, closes, and Alt+P brings it back |
| `screens.spec.js` | the screenshots in `docs/screenshots` |

Every flow runs in English and in Hindi, and each screen is checked for text in the other
language (Latin words in Hindi mode, Devanagari in English mode; product and challenge names,
quoted data, the user's own phrases and name excepted). Each test also fails on any console
error or warning, failed request, or 4xx or 5xx it didn't say it expects.

Last full run: 53 passed, 3 skipped (the phone-only screenshots and the once-a-run wrong invite
code, skipped on desktop), plus `uv run pytest`: 112 passed.

## 4. Quality checks

- **Console and network**: none in any end-to-end test, with three expected exceptions, each
  allowed by name: the 401 of `GET /auth/me` for a signed-out visitor (that is the session
  check, docs/API.md), the error statuses a test provokes on purpose, and headless Chrome's
  "GPU stall due to ReadPixels" warning, which comes from its software WebGL (the app never reads
  pixels). No 404 on any screen. `/favicon.ico` is answered with the app's HTML (there is no icon).
- **Lighthouse** (12, Playwright's Chromium, mock-mode server):

  | Page | Accessibility | Performance (before → after gzip) |
  | - | - | - |
  | Landing, phone | 100 | 60 → 74 |
  | Landing, desktop | 100 | 93 → 98 |
  | Speak (signed in), phone | 100 | 67 → 82 |
  | Speak (signed in), desktop | 100 | 98 → 100 |

  The server sent the 500 KB script uncompressed; `src/server.py` now gzips the web app's
  files (147 KB). What still slows a phone: the Google Fonts stylesheet blocks rendering, and
  the script is one 500 KB chunk.
- **Keyboard**: every Tab stop on every screen shows a focus ring, and every flow above works
  without a mouse. Nothing is modal, so nothing needs to trap focus: confirm boxes are inline and
  most move focus to their safe button. The bottom sheet and show-to-listener mode don't exist.
- **Reduced motion**: respected everywhere, including the background, which used to ignore a
  change made while the page was open.
- **Tap targets**: every control on every screen is now at least 44 px, as Settings promises
  (the EN / हिं buttons and the footer wordmark were not).
- **Screenshots**: 58, at 390 wide, both languages, in `docs/screenshots` (taken in mock mode,
  so what Prisma "heard" in them is made up). No page scrolls sideways. What they showed is in
  section 8.

## 5. Backend and security

- `uv run pytest`: 112 passed.
- **One user can't reach another's data**: every route with an id was already covered
  (`tests/test_api.py`, `tests/test_privacy.py`); a new test covers the routes without one
  (lists, stats, recognition candidates, `/speak`, `PATCH /me`, `DELETE /me/voice`, `DELETE /me`).
- **Cookie**: `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/` (new `tests/test_security.py`).
- **CORS**: none at all; another origin gets no `Access-Control-Allow-Origin` (new test).
- **Upload limits**: 10 MB, now refused from `Content-Length` before the body is read (it was
  read in full first); phrases 0.3 to 15 s, a voice 5 to 30 s (tests).
- **Rate limits**: 5 failed logins lock an email for 15 minutes (new test; it had none), 5 wrong
  invite codes lock an address, plus the daily cap per account and the server-wide call limit.
- **Secrets**: the real `GNANI_API_KEY` and `JWT_SECRET` values from `.env` appear in none of
  the 335 commits on any branch; the one pattern match is a made-up value in a test. `.gitignore`
  covers `.env`, `data/`, `logs/`, `web/certs/`, `web/reference/`; only the two default phrase
  lists under `data/` are tracked; `scripts/deploy_space.py --check-only` passes.
- **Docker**: the image builds; it holds the code, the built app, the phrase lists and the
  virtualenv, nothing else. `scripts/smoke_test.py` passes against it on port 7860 in mock mode
  (with `--voice`), and the image refuses to start with `GNANI_MOCK` and `TRUST_PROXY` together.

## 6. The real check

`scripts/smoke_test.py` gained one step: it now says the confirmed phrase aloud (the stock-voice
`/speak` was never exercised). With mock mode off, the Gnani key from `.env` (where it is commented
out), `GNANI_CALL_LIMIT=5`, and one Windows-synthesized recording of "I need help" passed as
both files, the run should cost 1 Prisma and 1 Timbre call.

**It made 1 Gnani call: the first enrollment's Prisma request, which Gnani refused with HTTP 401
(the key is not accepted).** The app answered `gnani_rejected` (502) and the smoke test stopped
there. Nothing else was sent. To run it with a working key, see "Before you submit".

## 7. Claims audit

Checked: the landing page (both languages), README.md, docs/WRITEUP.md, docs/POSTS.md, and also
the docs the README sends judges to (SUBMISSION_PACKAGE, DEMO_RUNBOOK, DEMO_VIDEO_PLAN,
DEMO_MATRIX, SUBMISSION_CHECKLIST). There are no results files (`results/` doesn't exist), and
every doc already said accuracy isn't measured.

| Claim | Where | Truth | Now |
| - | - | - | - |
| "full local data ownership", "Full data ownership" | POSTS | recordings go to Gnani and are kept on the server | removed |
| "caregiver contact alerts" | POSTS | a saved number and a WhatsApp link, no alerts | "a caregiver's number for a ready WhatsApp link" |
| "acoustic phonetic fingerprint(s)", "vocal tract characteristics", "matches the incoming audio" | POSTS, SUBMISSION_PACKAGE, DEMO_VIDEO_PLAN | fingerprints are Prisma's text transcripts | "the phrase's fingerprint: text, not audio" |
| "the transcription errors are consistent and reproducible", "a clinical observation" | POSTS, SUBMISSION_PACKAGE | the bet the app is built on, not measured | said as a bet |
| "word error rates exceeding 50%" | SUBMISSION_PACKAGE | no source | removed |
| "similarity scores", "similarity rankings", "confidence indicators", "waveform visualizer" | README, DEMO_VIDEO_PLAN, DEMO_RUNBOOK, SUBMISSION_PACKAGE | the screen shows the three phrases, best first, and "Maybe" | corrected |
| onboarding "consent confirmation, phrase category, practice recording, calibrates microphone" | SUBMISSION_PACKAGE | welcome, language, how it learns, getting ready | corrected |
| "high-contrast theme", "Clinic", "test slot substitution" | SUBMISSION_PACKAGE | focus outlines; Hospital; no building-block screens | corrected |
| `simulated` = "synthetically generated … controlled articulatory noise"; TORGO "consented" | SUBMISSION_PACKAGE | someone imitating unclear speech; TORGO's licence is unchecked (DEMO_DATA.md) | corrected |
| evaluate.py runs "without consuming live Gnani credits", "acoustic distance thresholds" | SUBMISSION_PACKAGE | it sends each held-out recording to Prisma once; no thresholds | corrected |
| "atomic" deletion that "wipes all audio and database records" | README, SUBMISSION_PACKAGE, DEMO_RUNBOOK, DEMO_VIDEO_PLAN, CHECKLIST | files first, then the rows in one transaction; call counts and the shared stock-voice cache stay (the README's privacy section already said so) | corrected |
| "falls back to browser offline speech synthesis" | README, DEMO_VIDEO_PLAN | the browser's own synthesis when Timbre fails; recognition still needs Prisma | corrected |
| "Demo (Simulated)" badge | README, DEMO_MATRIX | now "Simulated speech" | corrected |
| "100 tests", "100/100 passed", "built in <500ms", "Cold start (20 to 30s) … instantaneous" | SUBMISSION_PACKAGE, CHECKLIST | stale or unmeasured | removed |
| "Learns your voice" | landing (both languages) | it learns how Prisma hears this person's phrases | "Learns how you speak" |
| "It can match a phrase after its first recording" | landing FAQ | Speak now opens after the quick start | rewritten; also says an own-voice recording goes to Gnani once |
| "Sunn suggests 50 everyday phrases" | landing FAQ | 51 | 51 |
| own voice "Coming next … not built yet" | landing, DESIGN.md | built now (Settings) | "Optional … needs its own consent" |
| "Urgent phrases … given higher priority when speaking" | Phrases screen | urgency doesn't change the ranking | "get an Urgent label when Sunn suggests them" |
| "All interactive controls … 44px to 64px" | Settings screen | was not true for EN / हिं | made true |
| the welcome guide's language step | README, DEMO_RUNBOOK, DEMO_VIDEO_PLAN, SUBMISSION_PACKAGE | it also changed the spoken language | fixed in the app; the docs say it changes only the screen's language |

docs/WRITEUP.md needed no change. Medical claims: none found; every doc keeps "not a medical device".

## 8. Report

### What was broken, and what fixed it

Backend and scripts
- `src/api.py`: the default phrases and building blocks were added one commit each (about 120):
  `POST /me/phrases/default`, which sign-up waits for, took 0.4 s at best, 2.7 s (median) in the
  test runs and up to 46 s with a few users at once; now one transaction (112 ms median).
- `src/api.py`: an upload was read in full before the 10 MB check; bodies over the limit are now
  refused from `Content-Length`.
- `src/api.py`, `src/gnani.py`, `src/prisma.py`, `src/speak.py`, `src/gnani_mock.py`,
  `src/gnani_mock.json`: mock mode (section 1).
- `src/server.py`: the web app's script and CSS were sent uncompressed (500 KB); now gzipped.
- `scripts/smoke_test.py`: never called the stock-voice `/speak`; now says the confirmed phrase.
- `scripts/evaluate.py`: could have produced results from made-up transcripts; refuses mock mode.
- `tests/test_deploy.py`: the dry-run test failed whenever `.env` had no real Gnani key.

Web app
- `web/src/api.js`: Speak's default "Any" chip made every recognition fail (`context=any`, 422).
- `web/src/Progress.jsx`: crashed (`lang` undefined) as soon as any recognition was confirmed;
  the week column read "का हफ़्ता" in Hindi.
- `web/src/Settings.jsx`: the app-language toggle silently changed the spoken language; now
  local, with a separate spoken-language control that warns first.
- `web/src/Settings.jsx`: no way to add an own voice (the button went to Teach); upload added.
- `web/src/Settings.jsx`: the own-voice and focus toggles read "Reduced motion active".
- `web/src/Settings.jsx`: a bad phone number said "Something went wrong"; the check also
  allowed numbers the server refuses; the test sentence was in the app's language, not the
  spoken one, and misspelled the name.
- `web/src/Settings.jsx`, `web/src/Phrases.jsx`: "Settings saved" stayed in the old language
  after switching.
- `web/src/auth.jsx`, `web/src/AppShell.jsx`, `web/src/prefs.js`: log out and account deletion
  could end on `/login?next=…`; deletion left the account's local flag behind.
- `web/src/Enroll.jsx`, `web/src/Speak.jsx`, `web/src/Phrases.jsx`, `web/src/Landing.jsx`,
  `web/src/quickstart.js`: "needs recording" came from `enrolled` (any language); now
  `sample_count`, with the quick start and "Record again".
- `web/src/Phrases.jsx`: the filter name leaked in English into Hindi ("urgent").
- `web/src/SeaLight.jsx`: turning on Reduced motion didn't stop the background until a reload.
- `web/src/i18n/hi.js`: the name was spelled "सुन्न" ("numb") 17 times; now "सुन".
- `web/src/i18n/en.js`, `hi.js`: 9 API error codes had no words (`daily_cap_reached` said
  "Something went wrong"); all 24 now have a plain message in both languages.
- `web/src/styles.css`: onboarding's saffron step numbers leaked onto the landing page; the app
  header squeezed Log out to a sliver at 390; badges were ALL CAPS; the native file picker spoke
  the browser's language; two controls were under 44 px; single words were left alone on last
  lines, mostly in Hindi.
- `web/src/Speak.jsx`, `Progress.jsx`, `Settings.jsx`: user phrases and language names now carry
  their `lang`, for screen readers.
- `web/src/Onboarding.jsx`: the guide's language cards also sent `PATCH /me {language}`, silently
  changing the language the account speaks; now they change only the screen. Its last step said
  "ready to speak" once any phrase had 3 recordings in any language; now only once Speak is open.

### Still broken or risky

1. **The real Gnani check didn't pass**: the key in `.env` is refused (401).
2. **Speak stays closed until the 10 quick-start phrases have 3 recordings each.** A demo account
   must include them (docs/DEMO_DATA.md lists them). None of the 8 local accounts in
   `data/app.db` qualifies: none has recordings for more than one phrase.
3. **No accuracy results**: `results/` doesn't exist. Every doc says so.
4. **Not built**: SOS, show-to-listener, bottom sheet, building-block screens.
5. **Saffron outside the sun**: urgent badges, delete buttons, onboarding and the presenter bar
   use saffron, which DESIGN.md reserves for the sun and recording. A design decision, not changed.
6. **Phone performance**: Lighthouse 74 (landing) and 82 (Speak) on a throttled phone; one
   500 KB script and render-blocking Google Fonts.
7. **`/favicon.ico`** gets the app's HTML; there is no icon.
8. The free Space loses accounts and recordings on every restart (docs/DEPLOY.md).
9. `@Gnani_AI` in docs/POSTS.md is not verified as Gnani's handle.

### Before you submit (by hand)

1. Put a valid `GNANI_API_KEY` in `.env` (uncommented), then run the real check once:
   ```powershell
   docker build -t sunn-audit .
   docker run -d --name sunn-real -p 7860:7860 --env-file .env -e GNANI_CALL_LIMIT=5 sunn-audit
   uv run scripts/smoke_test.py speech.wav speech.wav --language en   # 1 Prisma + 1 Timbre call
   docker rm -f sunn-real
   ```
   (`speech.wav`: a few seconds of you saying "I need help".)
2. Record or load the demo account with the 10 quick-start phrases, 3 times each, with real
   speech and `GNANI_MOCK` off; give every recording its true source.
3. Deploy (`scripts/deploy_space.py`), with `TRUST_PROXY=1` and without `GNANI_MOCK` in the
   Space's settings; open it on a phone and check the microphone and playback.
4. Replace the placeholders in docs/POSTS.md and docs/SUBMISSION_PACKAGE.md; check `@Gnani_AI`.
5. Record the video from docs/DEMO_VIDEO_PLAN.md as updated.
6. Merge this branch into `main`.
