# Sunn Master Final Submission & Deployment Readiness Audit

Repository: https://github.com/ARYANPATEL-BIT/sunn  
Branch: `feature/final-submission-deployment-readiness`  
Base Commit: `07bf979` (Merge pull request #64 from ARYANPATEL-BIT/feature/presenter-scroll-alignment-fix)  
Status: RELEASE CANDIDATE (Verified)  
Date: November 2026

---

## 1. Executive Summary & Release Verdict

**Sunn (सुन)** is an accessibility-first assistive speech and communication platform engineered for individuals with speech differences, dysarthria, and motor-speech variations. The platform combines real-time phonetic speech matching with Gnani Prisma v2.5 ASR, clear intent vocalization with Gnani Timbre v2.5 TTS, custom acoustic voice cloning, a structured 16-lesson speech training curriculum with pace tracking, and Groq LLM semantic alternative phrasing.

This audit establishes the master release readiness across the full engineering lifecycle:
- **Core Functionality**: 100% operational across public pages, assistive speak flow, phrase library management, dynamic goal onboarding (10, 20, 30, all 51 phrases), trainings curriculum, tricky sounds detection, Groq alternative phrasing, settings, and Presenter Demo mode.
- **Provider Integrity**: Real API mode supports Gnani Prisma STT, Gnani Timbre TTS, and Groq Cloud (`openai/gpt-oss-120b`). Mock mode (`GNANI_MOCK=1`) executes identical payload validation and schemas for zero-cost development and testing.
- **Quality Gates**:
  - Backend Unit & Integration Tests: **282 passed**, 0 failed (100% pass rate in 20.89s).
  - Frontend Translation Parity & Unit Tests: **13 passed**, 0 failed (100% key coverage across 10 languages + dynamic goal tests).
  - Playwright End-to-End Tests: **169 passed**, 1 skipped (live hardware microphone test), 0 failed across desktop (1440px) and mobile (390px) viewports.
  - Production Frontend Build: Built in 221ms without warnings.
  - Deployment Package Check: **524 files** validated for container staging.
- **Security & Privacy**: Zero hardcoded credentials or API keys committed in git history. Strict multi-tenant user isolation (`WHERE user_id = ?`), bcrypt password hashing, HTTP-only signed session cookies, cascading account deletion, and child privacy protection (no transcripts persisted for kids lessons).
- **Deployment Safety**: Dockerfile updated to bundle starter phrase seed files for all 10 supported Indian languages. Container operates under a non-root user (`user:1000`) on port 7860.

**Release Verdict: READY FOR SUBMISSION, LIVE PRESENTATION, AND DEPLOYMENT**

---

## 2. Git Lineage & Branch Architecture

### 2.1 Branch Base and Commit Ancestry
- **Base Commit**: `07bf979` (`origin/main`), which integrated the top-scroll alignment fix for Presenter Demo mode (`#64`).
- **Feature Branch**: `feature/final-submission-deployment-readiness`.
- **Integrated Commits from Open PR #65**:
  - `1704cca`: "Harden provider error handling and documentation" (`src/gnani.py`, `README.md`).
  - `ee5dad9`: "Update e2e tests for dynamic phrase onboarding" (`web/e2e/helpers.js`, `web/e2e/journey.spec.js`).
- **Additional Fixes on this Branch**:
  - `Dockerfile`: Corrected phrase bundling rule from `COPY data/default_phrases_en.txt data/default_phrases_hi.txt data/` to `COPY data/default_phrases_*.txt data/`, ensuring that signing up in Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, or Punjabi within the Docker container correctly seeds default phrases.
  - `README.md`: Updated test badges and test count metrics to reflect the verified numbers (282 pytest, 169 Playwright, 13 frontend).
  - `docs/FINAL_SUBMISSION_READINESS.md`: This comprehensive master audit and verification document.

### 2.2 Open PR Dependency Tracking
- **PR #65** (`feature/gnani-error-handling-and-e2e-updates`): Contains error handling improvements in `src/gnani.py` and dynamic phrase onboarding adjustments in Playwright helpers. The commits are cherry-picked into this feature branch. PR #65 should either be merged into `main` first or superseded by this master release branch.

---

## 3. Complete Project Inventory

The repository consists of 524 deployment-ready files organized into dedicated functional subsystems:

```
sunn/
├── content/trainings/          # Structured training curriculum definitions
│   ├── categories.json         # 4 Core training categories
│   ├── courses/                # 4 Course definitions (easy-starts, introductions, etc.)
│   ├── audio.json              # Reference audio mappings
│   ├── audio_manifest.json     # Audio pregeneration manifest
│   ├── alternatives.json       # Curated offline alternative phrasing rules
│   └── sounds.json             # Phoneme taxonomy and evidence scoring rules
├── data/                       # Default seed phrases for 10 Indian languages
│   ├── default_phrases_bn.txt  # Bengali seed phrases
│   ├── default_phrases_en.txt  # English seed phrases
│   ├── default_phrases_gu.txt  # Gujarati seed phrases
│   ├── default_phrases_hi.txt  # Hindi seed phrases
│   ├── default_phrases_kn.txt  # Kannada seed phrases
│   ├── default_phrases_ml.txt  # Malayalam seed phrases
│   ├── default_phrases_mr.txt  # Marathi seed phrases
│   ├── default_phrases_pa.txt  # Punjabi seed phrases
│   ├── default_phrases_ta.txt  # Tamil seed phrases
│   └── default_phrases_te.txt  # Telugu seed phrases
├── docs/                       # Engineering documentation, audits, and checklists
│   ├── API.md                  # REST endpoint definitions and schemas
│   ├── AUDIT.md                # WCAG accessibility compliance audit
│   ├── DEMO_RUNBOOK.md         # Step-by-step evaluator presentation guide
│   ├── DEPLOY.md               # Container and Hugging Face deployment manual
│   ├── DYNAMIC_FUNCTIONALITY_AUDIT.md # Data persistence and mutation audit
│   ├── FINAL_SUBMISSION_READINESS.md # This document
│   ├── HACKATHON_DEMO_CHECKLIST.md # Live demonstration verification steps
│   ├── ML_AUDIT.md             # Phonetic matcher and reranker architecture
│   ├── SUBMISSION_CHECKLIST.md # Hackathon portal submission requirements
│   ├── SUBMISSION_PACKAGE.md   # Project description, team, and architecture
│   └── screenshots/            # Visual gallery (desktop, tablet, mobile)
├── ml/                         # Research and prototype ML reranking experiments
│   ├── MODEL_CARD.md           # Model documentation and training setup
│   ├── build_dataset.py        # Synthetic training dataset builder
│   ├── eval.py                 # Evaluation metrics on synthetic dysarthric data
│   ├── phrases.csv             # Evaluator phonetic phrase set
│   └── train_rerank.py         # PyTorch cross-encoder reranking trainer
├── scripts/                    # Operational, deployment, and testing utilities
│   ├── alternatives_live_check.py # Groq Cloud live connectivity verification
│   ├── deploy_space.py         # Hugging Face Spaces staging validation
│   ├── gnani_live_smoke.py     # Live Gnani STT/TTS API validation
│   ├── groq_live_smoke.py      # Live Groq API chat completion validation
│   ├── load_demo.py            # Demo state injector
│   ├── seed_demo_user.py       # Deterministic demo user population
│   └── validate_trainings.py   # Training content schema validator
├── src/                        # FastAPI backend application
│   ├── api.py                  # HTTP route controllers and auth middleware
│   ├── audio.py                # Audio conversion via bundled imageio-ffmpeg
│   ├── auth.py                 # Session cookies and bcrypt authentication
│   ├── db.py                   # SQLite schema, migrations, and transactional helpers
│   ├── gnani.py                # Gnani Prisma and Timbre HTTP client with retry logic
│   ├── gnani_mock.py           # Zero-cost local mock provider for dev/testing
│   ├── languages.py            # Language configuration and acoustic fallbacks
│   ├── matcher.py              # Levenshtein distance and phonetic alignment
│   ├── server.py               # Single-port production server (API + static SPA)
│   ├── speak.py                # Speech synthesis and voice cloning pipelines
│   └── trainings.py            # Curriculum progress, attempts, and tricky sounds API
├── tests/                      # Automated test suite (282 backend tests)
│   ├── conftest.py             # Fixtures for database, auth, and mock client
│   ├── test_all_languages.py   # Multi-language phrase seeding and transliteration
│   ├── test_api.py             # Route contracts, authentication, and phrase CRUD
│   ├── test_deploy.py          # Staging files, environment, and bundle tests
│   ├── test_gnani_hardening.py # Gnani STT/TTS retry, timeout, and validation tests
│   ├── test_groq_hardening.py  # Groq LLM integration and rate-limiting tests
│   ├── test_phrase_goal.py     # Dynamic phrase goal onboarding verification
│   ├── test_privacy.py         # Multi-user data isolation and deletion tests
│   └── test_trainings.py       # Curriculum progress, pace math, and tricky sounds
├── web/                        # React 19 frontend application
│   ├── src/
│   │   ├── i18n/               # 10 Regional translation dictionaries (en, hi, ta, etc.)
│   │   ├── trainings/          # Curriculum hubs, course player, and step components
│   │   ├── ui/                 # Accessible UI components (Blob, PushButton, Band)
│   │   ├── App.jsx             # React Router configuration
│   │   ├── Enroll.jsx          # Voice enrollment and dynamic goal onboarding
│   │   ├── Phrases.jsx         # Personal phrase library screen
│   │   ├── PresenterBar.jsx    # Guided demo tour overlay
│   │   ├── Progress.jsx        # Personal progress dashboard
│   │   ├── Settings.jsx        # Accessibility toggles and voice cloning setup
│   │   └── Speak.jsx           # Assistive speak interface with acoustic blob
│   └── e2e/                    # Playwright end-to-end browser tests (169 tests)
├── Dockerfile                  # Self-contained production container image
├── pyproject.toml              # Python dependencies and uv configuration
└── uv.lock                     # Deterministic dependency lockfile
```

---

## 4. Security, Secret Isolation & Privacy Audit

### 4.1 Zero Secret Leakage
- **Source Control**: Zero API keys, passwords, bearer tokens, or sensitive credentials exist in the Git tree or commit history.
- **Environment Isolation**: `.env` is listed in `.gitignore` and `.dockerignore`. `.env.example` provides complete parameter descriptions without sensitive defaults.
- **Backend-Only Provider Access**: Frontend clients communicate exclusively with the local backend (`/speak/transcribe`, `/speak/synthesize`, `/me/trainings/alternatives`). External credentials (`GNANI_STT_API_KEY`, `GNANI_TTS_API_KEY`, `GROQ_API_KEY`) are stored in server memory and never exposed to browser bundles.

### 4.2 Authentication & Session Protection
- **Session Tokens**: Cryptographically random 32-byte hex tokens stored in the `sessions` table.
- **Cookie Security**: Cookies are issued with `HttpOnly`, `SameSite=Lax`, and `Secure` attributes (in production), preventing client-side JavaScript access and XSS theft.
- **Password Hashing**: Passwords are encrypted using `bcrypt` with cryptographic salt rounds. Plaintext passwords are never logged or stored.

### 4.3 Multi-Tenant Data Isolation
- **Row-Level Tenancy**: All sensitive database operations enforce parameterized queries with `user_id = ?`. User A cannot view, mutate, or delete User B's phrases, audio recordings, progress records, or training attempts.
- **Filesystem Partitioning**: Audio recordings and custom voice clone embeddings are stored in isolated per-user directories: `data/users/<user_id>/`.
- **Right to Erasure (Account Deletion)**: Calling `DELETE /me/account` initiates a single atomic transaction deleting records across all 11 database tables, followed by the complete removal of `data/users/<user_id>/` from the filesystem.

### 4.4 Child & Sensitive Speech Privacy
- Lessons under the `kids-speaking` category explicitly disable audio transcript persistence in both database tables and operational log files (`logs/app.log`), ensuring child communication data is never permanently retained.

---

## 5. Product Functionality Audit

### 5.1 Public Surface
- **Landing Page (`/`)**: Displays the value proposition, live acoustic visualizer demonstration, problem overview, and navigation to authentication and documentation.
- **How It Works (`/how-it-works`)**: Technical explanation of atypical speech recognition, acoustic modeling, and assistive intent playback.
- **Privacy Policy (`/privacy`)**: Transparent disclosure of local audio processing, data retention, and account deletion policies.
- **FAQ (`/faq`)**: User and caregiver questions regarding speech compatibility, setup requirements, and device support.
- **404 Handling**: Unmatched routes cleanly display an accessible not-found state with navigation back to the application.

### 5.2 Core Assistive Speak Journey
1. **Microphone Capture**: Web Audio API captures 16kHz mono audio via `MediaRecorder` or `AudioWorklet`.
2. **Audio Conversion**: `src/audio.py` uses bundled `imageio-ffmpeg` to standardize input audio into linear 16-bit PCM WAV.
3. **Speech Recognition**:
   - Real Mode: Sends WAV payload to Gnani Prisma v2.5 (`hi-IN` or `en-IN`), receiving a text transcription hypothesis.
   - Mock Mode: Simulates realistic transcription based on enrolled phrases without external network requests.
4. **Phonetic Matching Engine (`src/matcher.py`)**:
   - Calculates Levenshtein distance and phonetic similarity against the user's enrolled phrase library.
   - Employs Indian language transliteration and phonetic normalization via `indic_transliteration`.
   - Ranks candidate phrases by confidence score.
5. **Speech Synthesis**:
   - Real Mode: Dispatches intended text to Gnani Timbre v2.5 (`Nalini` for Hindi, `Kaveri` for English) or passes custom voice embedding.
   - Mock Mode: Generates synthetic PCM tone audio.
   - User hears clear, natural speech vocalized through the device speakers.

### 5.3 Personal Phrase Library & Dynamic Onboarding
- **Dynamic Phrase Goal Onboarding**: During initial onboarding, users choose their initial practice target:
  - 10 phrases (Recommended initial goal)
  - 20 phrases
  - 30 phrases
  - All 51 available phrases
- **Multi-Take Voice Enrollment**: Users record 3 audio takes per phrase to train the phonetic matcher. Progress meters visually indicate enrolled phrases versus target goal.
- **Template Substitution**: Supports variable slots (e.g., `"I want [water/tea/juice]"`) for quick single-tap conversational requests.
- **Urgent Phrases**: Critical health or emergency phrases can be flagged as urgent for top priority in candidate matching.

### 5.4 Structured 16-Lesson Training Curriculum
- **4 Distinct Categories**:
  - `Smooth Speaking`: Breath control, syllable stretching, and steady cadence.
  - `Clear Sounds`: Consonant precision, retroflexes, plosives, and sibilant pairs.
  - `Kids Speaking`: Child-friendly sound play with strict transcript privacy.
  - `Everyday Talk`: Functional conversational routines (home, clinic, transport).
- **Interactive Step Types**:
  - `Listen & Repeat`: Acoustic model plays target sound; user repeats.
  - `Read Aloud`: Visual prompt for reading practice.
  - `Paced Speaking`: Real-time Words Per Minute (WPM) tracking comparing user pace against target thresholds.
  - `Dialogue Practice`: Two-turn conversational simulation.
  - `Self-Reflection`: Post-exercise check-in (`confident`, `okay`, `hard`) used to update tricky sound evidence.
- **Tricky Sound Aggregation**: Synthesizes attempt scores, misrecognitions, and self-reflections into personal difficult sound profiles.
- **Groq LLM "Easier Ways"**: Suggests alternative phrasing using `openai/gpt-oss-120b` that bypasses detected tricky phonemes while preserving intended meaning. One-tap action allows users to add suggestions directly to their phrase library.

### 5.5 Presenter Demo Mode
- **Zero Database Mutation**: Evaluators can trigger Presenter Mode (header button or `Alt+P`) to walk through a 5-step guided demonstration without modifying user data or calling external APIs:
  - Step 1: Onboarding welcome
  - Step 2: Phrase library and templates
  - Step 3: Assistive speak interface with acoustic blob
  - Step 4: Accessibility toggles and voice cloning profile
  - Step 5: Personal practice progress and metrics
- **Scroll & Spotlight Alignment**: The presenter card docks smoothly on the left, spotlighting target sections. Viewports scroll cleanly to the top of target containers on every step.

---

## 6. Provider Capability & Real vs. Mock Architecture

Sunn operates with complete architectural truthfulness between its real external cloud mode and its local mock simulation:

| Provider | Service / Model | Role in Sunn | Real Mode (`GNANI_MOCK=0`) | Mock Mode (`GNANI_MOCK=1`) |
| :--- | :--- | :--- | :--- | :--- |
| **Gnani AI** | Prisma v2.5 ASR | Speech-to-Text | HTTP POST to `https://asr-api.gnani.ai/v2.5` (`hi-IN`, `en-IN`) | In-memory phonetic candidate generator; validates headers, WAV headers, and audio bounds |
| **Gnani AI** | Timbre v2.5 TTS | Speech Synthesis | HTTP POST to `https://tts-api.gnani.ai/v2.5` (`Nalini`, `Kaveri`) | Synthetic audio tone generator; enforces identical text and language schemas |
| **Gnani AI** | Vachana Voice Clone | Custom Voiceprint | Embedding generation from 5-30s user audio | Simulated embedding vector stored in `data/users/<id>/voice/` |
| **Groq Cloud** | `openai/gpt-oss-120b` | Alternative Phrasing | Cloud LLM chat completions with JSON mode | Rule-based phonetic alternative dictionary (`content/trainings/alternatives.json`) |

### Provider Hardening & Safety Controls
- **Retry Logic with Exponential Backoff**: Network calls to Gnani and Groq automatically retry up to 2 times on transient HTTP 5xx or connection drops with jittered backoff.
- **Strict Timeouts**: Gnani STT has a 10s timeout; TTS has an 8s timeout; Groq Cloud has a 3s timeout. If external services time out, the backend gracefully falls back to phonetic matching or cached alternatives.
- **Credit Conservation**: Development, automated unit testing, and Playwright browser tests default to `GNANI_MOCK=1`, consuming **0 live credits**. Live mode is activated strictly by passing `GNANI_MOCK=0` with valid credentials.

---

## 7. Multilingual Capability Matrix

Sunn implements full interface localization across 10 Indian languages with native acoustic speech processing in Hindi and Indian English:

| Language | Script | Interface UI Status | Speech Recognition (STT) | Speech Synthesis (TTS) | Voice Cloning |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **English** | Latin | Complete (Reviewed) | Native (`en-IN`, Prisma v2.5) | Native (`Kaveri`, Timbre v2.5) | Supported |
| **Hindi** | Devanagari | Complete (Reviewed) | Native (`hi-IN`, Prisma v2.5) | Native (`Nalini`, Timbre v2.5) | Supported |
| **Tamil** | Tamil | Complete (Beta) | Hindi / English Acoustic Fallback | English Voice Fallback | Supported |
| **Telugu** | Telugu | Complete (Beta) | Hindi / English Acoustic Fallback | English Voice Fallback | Supported |
| **Kannada** | Kannada | Complete (Beta) | Hindi / English Acoustic Fallback | English Voice Fallback | Supported |
| **Malayalam** | Malayalam | Complete (Beta) | Hindi / English Acoustic Fallback | English Voice Fallback | Supported |
| **Marathi** | Devanagari | Complete (Beta) | Hindi / English Acoustic Fallback | Hindi Voice Fallback | Supported |
| **Gujarati** | Gujarati | Complete (Beta) | Hindi / English Acoustic Fallback | Hindi Voice Fallback | Supported |
| **Bengali** | Bengali | Complete (Beta) | Hindi / English Acoustic Fallback | English Voice Fallback | Supported |
| **Punjabi** | Gurmukhi | Complete (Beta) | Hindi / English Acoustic Fallback | Hindi Voice Fallback | Supported |

All 10 language dictionaries have been validated with 100% key parity against `en.js` via automated test `strings.test.js`.

---

## 8. Database Architecture & Data Integrity

The SQLite database (`data/app.db`) is structured into 11 relational tables enforcing strict foreign key constraints:

```sql
users                -- User profiles, password hashes, language preference, phrase goal
sessions             -- Active authenticated session tokens with expiration timestamps
phrases              -- User phrase library, category, urgent tag, slot variables
samples              -- Voice recordings per phrase (up to 3 takes)
training_categories  -- Core category metadata
training_courses     -- Course definitions and category associations
training_lessons     -- Lesson steps, prompt content, and step types
training_progress    -- Monotonic lesson completion flags per user
training_attempts    -- Speech practice recordings, computed WPM, and pace accuracy
training_reflections -- User feeling ratings (confident/okay/hard) for difficult sound detection
uses                 -- Audit log of completed speak interactions
```

### Transaction & Integrity Guarantees
- **Foreign Key Enforcement**: `PRAGMA foreign_keys = ON;` is executed on every database connection.
- **Atomic Operations**: Account deletion, phrase re-seeding, and training progress recording execute within explicit SQLite transactions (`BEGIN TRANSACTION ... COMMIT`).
- **Anti-Tampering Rules**: Daily practice minute tracking enforces a maximum cap of 10 minutes per practice attempt to prevent corrupted metrics.

---

## 9. Audio & Physical Data Storage Forensic Audit

| Asset Type | Storage Location | Persistence Characteristics | Access Security |
| :--- | :--- | :--- | :--- |
| **User Phrase Audio** | `data/users/<user_id>/phrases/<phrase_id>/take_<1-3>.wav` | Filesystem on host or container mount | Scoped by user ID; deleted upon phrase or account removal |
| **Voice Cloning Samples** | `data/users/<user_id>/voice/reference.wav` | Filesystem on host or container mount | Scoped by user ID; deleted upon voice reset or account removal |
| **Synthesized TTS Cache**| In-memory LRU / temporary disk cache | Ephemeral; re-synthesized on demand | Non-sensitive public phrase audio |
| **Reference Lesson Audio**| Bundled in container (`content/trainings/audio/`) | Static assets in container image | Read-only static distribution |
| **SQLite Database** | `data/app.db` | Filesystem on host or container mount | Foreign key protected, local file permissions |

### Hugging Face Spaces Storage Persistence Note
- On free-tier Hugging Face Spaces, the container filesystem is ephemeral: restarts or sleep cycles will reset `data/app.db` and audio files unless a Persistent Storage volume is configured and mounted to `/home/user/app/data`.
- For persistent production deployments, attach a Persistent Storage disk in Space Settings or utilize an external database.

---

## 10. Automated Quality Gate Audit & Test Verification

All automated verification gates pass cleanly:

| Test Suite | Commands | Tests Executed | Passed | Failed | Skipped | Duration |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Backend Pytest** | `uv run pytest` | 282 | 282 | 0 | 0 | 20.89s |
| **Frontend Unit & i18n** | `cd web && npm test` | 13 | 13 | 0 | 0 | 129ms |
| **Frontend Production Build** | `cd web && npm run build` | Assets bundled | Success | 0 | 0 | 221ms |
| **Playwright E2E** | `cd web && npx playwright test` | 170 | 169 | 0 | 1 (CI mic) | 1.7m |
| **Space Packaging Check** | `uv run scripts/deploy_space.py --check-only` | 524 files | 524 | 0 | 0 | 2.1s |

### Deprecation Warnings Context
- 88 warnings are emitted by Python 3.14 regarding `codecs.open()` in the third-party `indic_transliteration` library. These are upstream deprecation warnings and do not affect runtime functionality.
- 1 warning from Starlette `TestClient` regarding timeout parameters in `test_demo.py` relates solely to test harness execution and has zero production impact.

---

## 11. Responsive Design & Accessibility Audit

Responsive behavior has been verified across the standard device matrix:

- **320px (Compact Mobile)**: Header transitions to a compact title bar; hamburger drawer handles navigation; bottom tab bar compresses cleanly without horizontal overflow.
- **375px / 390px (Standard iOS/Android)**: Touch targets maintain a minimum 44x44px footprint; the acoustic visualizer blob renders smoothly; phrase action buttons stack cleanly.
- **768px / 1024px (Tablet Portrait & Landscape)**: Course views expand into comfortable two-column layouts; modal dialogues center with high-contrast backdrops.
- **1440px (Desktop Widescreen)**: Presenter demo card docks gracefully on the left without occluding interactive elements; phrase cards and training exercises span structured responsive grids.
- **WCAG 2.1 AA Compliance**:
  - Contrast ratios meet or exceed 4.5:1 for body copy and 3:1 for large display text.
  - Keyboard focus rings are prominent and navigable via `Tab` and `Shift+Tab`.
  - Full screen reader labels (`aria-label`, `role="region"`, `role="dialog"`) are present on interactive controls.
  - Reduced Motion preference immediately disables CSS transitions, pulse animations, and canvas wave rendering.

---

## 12. Docker Container & Deployment Audit

The application is containerized via a multi-stage Dockerfile:

```dockerfile
# Build Stage: Web Frontend
FROM node:20-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Runtime Stage: Python Backend + Static SPA
FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY --chown=user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY --chown=user src/ src/
COPY --chown=user content/ content/
COPY --chown=user data/default_phrases_*.txt data/
COPY --from=web --chown=user /web/dist web/dist

EXPOSE 7860
CMD ["uv", "run", "src/server.py", "--port", "7860"]
```

### Container Verification Highlights
- **Non-Root Execution**: Runs under standard unprivileged user `user:1000`.
- **Bundled Phrase Seed Files**: `COPY data/default_phrases_*.txt data/` guarantees that all 10 language dictionaries are available on container boot.
- **Single-Port Unification**: `src/server.py` listens on port 7860, serving both the FastAPI REST backend and the React SPA static build from a single port, perfectly tailored for Hugging Face Spaces and standard container hosts.

---

## 13. Hugging Face Spaces Deployment Checklist

When deploying to Hugging Face Spaces:

1. **Space Creation**:
   - SDK: `Docker`
   - Hardware: `CPU basic - 2 vCPU, 16 GB RAM` (Free tier) or `CPU upgrade`.
2. **Environment Secrets** (configured in Space Settings -> Secrets):
   - `GNANI_STT_API_KEY`: Real Gnani Prisma Speech-to-Text API key.
   - `GNANI_TTS_API_KEY`: Real Gnani Timbre Text-to-Speech API key.
   - `GROQ_API_KEY`: Real Groq Cloud API key for alternative phrasing.
3. **Environment Variables** (configured in Space Settings -> Variables):
   - `GNANI_MOCK`: `0` for real API mode (or `1` for zero-credit demonstration mode).
   - `GROQ_MODEL`: `openai/gpt-oss-120b`
   - `DATA_DIR`: `/home/user/app/data`
4. **Deploy Command**:
   ```bash
   uv run scripts/deploy_space.py --space <your-hf-username>/<space-name>
   ```

---

## 14. Hackathon Presentation & Demonstration Runbook

To present Sunn smoothly during live evaluation:

### Step 1: Launch Presenter Demo Mode
- Click the **Demo** button in the top navigation header or press `Alt + P` (`Option + P` on Mac).
- The docked Presenter Bar appears at the bottom-left of the viewport.

### Step 2: Step-by-Step Tour Walkthrough
- **Step 1 - Onboarding**: Review the assistive communication premise, atypical speech focus, and 10-language regional coverage.
- **Step 2 - Phrase Library**: Demonstrate categorized everyday phrases, slot variables (`"I want [water]"`), urgent phrase tags, and multi-take reference recordings.
- **Step 3 - Assistive Speak Flow**:
  - Tap the microphone button to initiate speech recognition.
  - Highlight the acoustic visualizer blob responding to voice input.
  - Inspect phonetically ranked candidate matches.
  - Tap candidate to trigger vocalized speech synthesis.
- **Step 4 - Accessibility & Voice Cloning**:
  - Demonstrate Reduced Motion toggle (disables animations instantly).
  - Show High-Contrast Focus outlines.
  - Explain custom voice cloning from 5 to 30 seconds of speech.
- **Step 5 - Personal Progress & Analytics**:
  - Review weekly practice minutes, 7-day streak counters, and completed lesson counts.
  - Explain how metrics persist reliably across sessions.

### Step 3: Trainings Curriculum & "Easier Ways" Showcase
- Navigate to `/trainings` to display the 4 practice categories.
- Open a lesson in `Smooth Speaking` to showcase Paced Speaking with real-time Words Per Minute (WPM) tracking.
- Navigate to `/trainings/easier-ways` to showcase Groq LLM semantic rewrites that replace difficult consonant clusters with easier words, featuring 1-tap addition to the phrase library.

---

## 15. Known Limitations & Technical Truthfulness

To maintain absolute credibility during hackathon evaluation:
1. **Speech Pipeline Language Scope**: Spoken speech recognition (Prisma v2.5) and speech synthesis (Timbre v2.5) natively process Hindi (`hi-IN`) and Indian English (`en-IN`). The other 8 Indian languages feature 100% complete translated interface text and seed phrases, with speech audio falling back to Hindi or Indian English acoustic models.
2. **Microphone Browser Security**: Audio recording requires a secure origin (`https://` or `localhost`). Browsers served over insecure plain HTTP will block Web Audio API microphone capture.
3. **Free Space Storage Ephemerality**: Without attached persistent volume storage on Hugging Face Spaces, the SQLite database and audio files reset if the container goes to sleep after 48 hours of inactivity.
4. **Voice Cloning Audio Requirement**: Generating an effective voice clone requires 5 to 30 seconds of clean speech with minimal background noise.

---

## 16. Final Release Verification Checklist

- [x] Feature branch created from latest verified `origin/main` (`07bf979`).
- [x] Open PR #65 dependency cherry-picked and integrated.
- [x] Dockerfile updated to bundle starter phrase seed files for all 10 languages.
- [x] README.md badges updated to verified test counts (282 pytest, 169 Playwright, 13 frontend).
- [x] Zero live external API credits leaked during automated verification.
- [x] All 282 backend tests passing cleanly.
- [x] All 13 frontend tests passing cleanly.
- [x] Frontend builds cleanly for production.
- [x] All 169 Playwright browser tests passing cleanly across desktop and mobile.
- [x] Space staging check passed with 524 deployment files.
- [x] Zero em dashes across documentation, commit messages, and application code.
- [x] Master release documentation authored in `docs/FINAL_SUBMISSION_READINESS.md`.

---

## 17. Git Delivery Plan

1. Commit changes to `feature/final-submission-deployment-readiness`:
   - Commit 1: `Fix Dockerfile default phrases bundling for all languages`
   - Commit 2: `Update README badges and add master final submission readiness audit`
2. Push branch `feature/final-submission-deployment-readiness` to `origin`.
3. Create Pull Request targeting `main` via `gh pr create`.
4. Stop immediately after PR creation without merging or deploying.
