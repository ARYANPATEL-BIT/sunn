# Challenge Submission Readiness Checklist

This document tracks all submission deliverables for the Gnani Great Indian AI Internship Challenge. It clearly demarcates items completed in the repository versus manual actions required from the team before the submission deadline.

---

## 1. Automated Repository Deliverables (Completed)

| Item | Requirement | Verification Location | Status |
| :--- | :--- | :--- | :--- |
| **Codebase & Architecture** | Full-stack application with FastAPI backend, SQLite, React 19 frontend | `src/`, `web/src/` | **Complete** |
| **Gnani API Integration** | Prisma STT verbatim transcribing, Timbre TTS v2.5 synthesis, voice cloning | `src/prisma.py`, `src/speak.py`, `src/gnani.py` | **Complete** |
| **Multi-Language Support** | Full Hindi (`hi`) and Indian English (`en`) support with 100% i18n key parity | `web/src/i18n/en.js`, `web/src/i18n/hi.js` | **Complete** |
| **Accessible Design** | WCAG AA contrast, Large Text, Enhanced Focus, Reduced Motion | `web/src/prefs.js`, `web/src/styles.css` | **Complete** |
| **Privacy & Consent** | Standalone voice consent, session cookie auth, atomic account deletion | `src/api.py`, `tests/test_privacy.py` | **Complete** |
| **Presenter Demo Mode** | Collapsible cue bar, 5-step navigation, provenance badges (`pilot`, `simulated`) | `web/src/PresenterBar.jsx` | **Complete** |
| **Resilient TTS Fallback** | Automatic client-side Web Speech API playback when Gnani TTS is unreachable | `web/src/api.js`, `web/src/Speak.jsx` | **Complete** |
| **Automated Test Suite** | 88 passing backend pytest tests covering API, contracts, privacy, and demo logic | `uv run pytest` | **Complete (88/88 passed)** |
| **Production Build** | Clean Vite build producing production bundles without errors | `cd web && npm run build` | **Complete (built in <500ms)** |
| **Deployment Package** | Single Docker image serving API on `/api` and web app on port 7860 | `Dockerfile`, `src/server.py`, `docs/DEPLOY.md` | **Complete** |
| **Challenge Write-Up** | Comprehensive solution overview, user personas, and technical write-up | `docs/WRITEUP.md` | **Complete** |
| **Social Media Posts** | Drafts for LinkedIn and X announcements | `docs/POSTS.md` | **Complete** |

---

## 2. Live Demo Deployment (Space Verification)

- **Hugging Face Docker Space**:
  - Script available: `python scripts/deploy_space.py`
  - Prerequisites: Hugging Face account and Space token configured.
  - Required Space Secrets:
    - `GNANI_API_KEY`: Active API key for Gnani Prisma and Timbre services.
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
  - Replace `[teammate]` and `[demo link]` with real handles and the live Space address.
  - Tag Gnani AI and include relevant hashtags.
- [ ] **Submit Challenge Form**:
  - Submit the repository link: `https://github.com/ARYANPATEL-BIT/sunn`.
  - Submit the live Space link: `https://<space>.hf.space`.
  - Submit the demo video link and write-up link (`docs/WRITEUP.md`).
