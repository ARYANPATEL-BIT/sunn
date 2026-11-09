# Challenge Submission Readiness Checklist

This document tracks all submission deliverables for the Gnani Great Indian AI Internship Challenge. It clearly demarcates items completed in the repository versus manual actions required from the team before the submission deadline.

---

## 1. Automated Repository Deliverables (Completed)

| Item | Requirement | Verification Location | Status |
| :--- | :--- | :--- | :--- |
| **Codebase & Architecture** | Full-stack application with FastAPI backend, SQLite, React 19 frontend | `src/`, `web/src/` | **Complete** |
| **Gnani API Integration** | Prisma STT verbatim transcribing, Timbre TTS v2.5 synthesis, voice cloning | `src/prisma.py`, `src/speak.py`, `src/gnani.py` | **Complete** |
| **Multi-Language Support** | Full Hindi (`hi`) and Indian English (`en`) support with 100% i18n key parity | `web/src/i18n/en.js`, `web/src/i18n/hi.js` | **Complete** |
| **Accessible Design** | Text colours chosen for WCAG AA contrast, Large text, High-contrast focus outlines, Reduced motion, 44px tap areas; Lighthouse accessibility 100 on the landing page and Speak (docs/AUDIT.md) | `web/src/prefs.js`, `web/src/styles.css` | **Complete** |
| **Privacy & Consent** | Standalone voice consent, session cookie auth, account deletion (files, then one database transaction) | `src/api.py`, `tests/test_privacy.py` | **Complete** |
| **Presenter Demo Mode** | Collapsible cue bar, 5-step navigation, provenance badges (`pilot`, `simulated`) | `web/src/PresenterBar.jsx` | **Complete** |
| **Resilient TTS Fallback** | Automatic client-side Web Speech API playback when Gnani TTS is unreachable | `web/src/api.js`, `web/src/Speak.jsx` | **Complete** |
| **Health Probe & Operations** | Liveness health probe at `/api/health` and `/health`, log rotation | `src/api.py`, `src/server.py`, `tests/test_deploy.py` | **Complete** |
| **Deployment Security Guard** | Invite code restriction in UI & API, path traversal protection, quota enforcement | `web/src/AuthPages.jsx`, `tests/test_deploy.py`, `docs/DEPLOY.md` | **Complete** |
| **Automated Test Suite** | Backend tests covering API, contracts, privacy, deploy, and demo logic; end-to-end tests of every screen in both languages (counts in docs/AUDIT.md) | `uv run pytest`, `cd web; npm run e2e` | **Complete (all pass)** |
| **Production Build** | Clean Vite build producing production bundles without errors | `cd web && npm run build` | **Complete** |
| **Deployment Package** | Single Docker image serving API on `/api` and web app on port 7860 | `Dockerfile`, `src/server.py`, `docs/DEPLOY.md` | **Complete** |
| **Challenge Write-Up** | Comprehensive solution overview, user personas, and technical write-up | `docs/WRITEUP.md` | **Complete** |
| **Submission Package** | Unified judge-facing documentation, dry run, and evaluation runbook | `docs/SUBMISSION_PACKAGE.md` | **Complete** |
| **Social Media Posts** | Drafts for LinkedIn and X announcements | `docs/POSTS.md` | **Complete** |

---

## 2. Live Demo Deployment (Space Verification)

- **Hugging Face Docker Space**:
  - Script available: `python scripts/deploy_space.py`
  - Prerequisites: Hugging Face account and Space token configured.
  - Required Space Secrets:
    - `GNANI_STT_API_KEY`: Active API key for Gnani Prisma Speech-to-Text service.
    - `GNANI_TTS_API_KEY`: Active API key for Gnani Timbre Text-to-Speech service.
    - `GROQ_API_KEY`: Optional API key for Groq AI assistant features.
    - `JWT_SECRET`: Random 48-byte URL-safe string.
    - `TRUST_PROXY`: `1` (required for correct client IP detection behind HF proxy).
    - `DEMO_INVITE_CODE`: Optional invite code to prevent unauthorized traffic.

---

## 3. Manual Team Actions Required Before Submission

The following actions require human authorization or manual external execution and must be completed by the team:

- [ ] **Record Demo Video**:
  - Follow the storyboard and script in `docs/DEMO_VIDEO_PLAN.md`.
  - Record the 3-minute screen capture walkthrough.
  - Upload to YouTube, Vimeo, or Google Drive as specified by the challenge guidelines.
- [ ] **Verify Hugging Face Space URL**:
  - Deploy the latest commit to the live Hugging Face Space using `python scripts/deploy_space.py`.
  - Test the live Space URL in desktop Chrome to verify microphone permissions and speech playback.
- [ ] **Publish LinkedIn and X Posts**:
  - Use the prepared copy in `docs/POSTS.md`.
  - Replace the bracketed placeholders (`[teammate name/handle]`, `[live demo link]`, `[demo video link]`, `[writeup link]`, `[github repository link]`) with real handles and links.
  - Tag Gnani AI and include relevant hashtags.
- [ ] **Work through "Before you submit" in `docs/AUDIT.md`** (a valid Gnani key, the real check, the demo account's quick-start phrases).
- [ ] **Submit Challenge Form**:
  - Submit the repository link: `https://github.com/ARYANPATEL-BIT/sunn`.
  - Submit the live Space link: `https://<space>.hf.space`.
  - Submit the demo video link and write-up link (`docs/WRITEUP.md`).
