# Live Demo and Service Dependency Matrix

This matrix documents which Sunn features require live external services, which operate locally or from cache, and how the system behaves if a network connection or API service is unavailable.

## Service Dependency Matrix

| Feature / Step | Live Service Required | Environment Variables | Fallback Mechanism | Behavior on Failure | Tested Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Account Creation & Login** | None (Local SQLite + Argon2id) | `JWT_SECRET` | None needed | Returns standard error (`bad_login`, `email_taken`) | Verified in test suite |
| **First-Time Onboarding** | None (Local React UI) | None | None needed | Graceful client-side recovery | Verified in test suite |
| **Everyday Phrase Bank** | None (Local text lists) | None | None needed | Adds 51 built-in everyday phrases | Verified in test suite |
| **Phrase Library CRUD** | None (Local SQLite) | None | None needed | Atomic transaction updates | Verified in test suite |
| **Speech Recognition (STT)** | Gnani Prisma STT (`stt/v3`) | `GNANI_API_KEY` | Local disk cache (`DATA_DIR/cache/prisma`) | Returns `gnani_unreachable` or `gnani_rejected` (502), `credit_limit_reached` or `daily_cap_reached` (429) | Verified in test suite (faked Gnani) and with disk cache |
| **Speech Synthesis (TTS)** | Gnani Timbre TTS (`timbre-v2.5`) | `GNANI_API_KEY` | Browser Web Speech API (`window.speechSynthesis`) | Automatically speaks via browser voice with visual notice | Verified in test suite and client code |
| **Voice Cloning** | Gnani Voice Clone (`vachana-vc-v1`) | `GNANI_API_KEY` | Stock Timbre voice | If cloning fails, nothing changes: the stock voice (Nalini or Kaveri) keeps speaking | Verified in test suite |
| **Accessibility Settings** | None (Client localStorage) | None | System preferences fallback (`prefers-reduced-motion`) | Falls back to default contrast and motion | Verified in test suite |
| **Progress Metrics** | None (Local database queries) | None | Empty state guidance | Displays clear non-medical explanation | Verified in test suite |
| **Account & Voice Deletion** | None (Local file & DB cascade) | None | None needed | Deletes the account's recordings, cached transcripts and cloned voice, then its rows in one transaction | Verified in test suite |
| **Presenter Mode & Cues** | None (Client-side presenter bar) | None | Manual tab navigation | Collapses to compact header pill | Verified in test suite |

## Live vs Fallback Communication Rules

1. **Prisma Speech Recognition**:
   - First-time recordings for a phrase require a live connection to Gnani Prisma.
   - Repeated recordings matching an identical audio hash are answered directly from the local disk cache without consuming Gnani API credits.
   - If Prisma is unreachable, the app presents an error notice. The app never fabricates transcripts as live recognition. The one exception is `GNANI_MOCK=1`, for local testing only: it says so loudly at startup and refuses to run behind a proxy, so it can't run on the Space.
2. **Timbre Speech Synthesis & Fallback**:
   - When Gnani Timbre is accessible, speech is synthesized via Gnani hosted neural voices (Nalini for Hindi, Kaveri for English).
   - If Gnani Timbre fails, times out, or reaches its credit cap, the app automatically switches to the browser's built-in speech synthesizer and displays: "Playing with browser speech synthesis fallback because the speech service is unavailable."
   - Presenters must point out this visual notice so judges know the difference between Gnani cloud synthesis and local device fallback.
3. **Demo Data Sources**:
   - Pre-loaded phrases carry explicit provenance badges (`Demo (Pilot)`, `Demo (TORGO)`, `Simulated speech`).
   - Untagged phrases are live recordings created directly in the application.
