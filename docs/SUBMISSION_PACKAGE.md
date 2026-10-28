# Sunn Challenge Submission Package

- **Challenge**: Gnani AI's Great Indian AI Internship Challenge
- **Project**: Sunn (सुन)
- **Category**: Speech AI / Assistive Technology
- **Primary Languages**: Hindi (`hi-IN`) and Indian English (`en-IN`)

---

## 1. Executive Summary and Problem Statement

Sunn is a speech aid for people with dysarthria, the slurred, slow or uneven speech that can come with a stroke, cerebral palsy, Parkinson's disease or motor neuron disease.

### The Speech Challenge
Standard automatic speech recognition (ASR) engines are predominantly trained on neurotypical speech. When presented with dysarthric speech (marked by slurred articulation, variable phonation, or reduced breath control), off-the-shelf recognizers often get it wrong. This forces individuals with atypical speech to rely on manual pointing, typing on boards, or continuous translation by family members.

### Sunn's Core Idea: Error Fingerprints
Sunn does not attempt to repair the general speech recognizer or train a model. Instead, it makes a bet: **a recognizer tends to mishear the same person's phrase in a similar way each time**. We have not yet measured how often that holds (see Results in README.md).

1. A user records each everyday phrase about 3 times during enrollment, and Gnani's Prisma STT transcribes each recording, often not quite right.
2. The bet is that Prisma's mistakes for that person and phrase are **similar each time**.
3. Sunn stores those transcripts as the phrase's **fingerprint**: text, not audio.
4. When the user speaks later, Sunn compares the new transcript with every fingerprint by edit distance, with a small boost for the chosen place (Home, Hospital, Market) and for frequent phrases, and shows the 3 closest phrases.
5. Upon confirmation, the phrase is vocalized clearly using Gnani's Timbre TTS (Nalini in Hindi, Kaveri in English) or the browser's Web Speech API fallback.

---

## 2. Technical Architecture and Stack

| Component | Technology | Role and Implementation Details |
| :--- | :--- | :--- |
| **Frontend** | React 19, Vite, Plain CSS | Responsive single-page application, high-contrast focus outlines, large tap targets, MediaRecorder audio recorder, Web Speech API fallback. |
| **Backend API** | FastAPI, Python 3.13 / 3.14 | RESTful ASGI backend serving endpoints under `/api`, token authentication, audio conversion via `imageio-ffmpeg`. |
| **Speech-to-Text** | Gnani Prisma STT | Transcribes incoming WAV audio samples (16 kHz mono 16-bit PCM). |
| **Text-to-Speech** | Gnani Timbre TTS v2.5 | Synthesizes confirmed phrases aloud (`Nalini` for Hindi, `Kaveri` for Indian English). |
| **Local Speech Fallback** | Browser Web Speech API | Client-side `window.speechSynthesis` provides immediate vocalization if offline or API limits are reached. |
| **Database & Storage** | SQLite (`app.db`), Local Disk | Every account in one SQLite database on the server, recordings in per-user folders; one person's recordings are never matched against another's. |
| **Deployment** | Docker, Uvicorn | Single container image serving both API and static frontend on port 7860. |

### Truthful Limitations and Non-Medical Disclaimer
- **Not a Medical Device**: Sunn is a communication assistance tool. It does not diagnose, treat, prevent, or measure speech disorders. The Progress dashboard displays usage and recognition trends, not clinical therapy metrics.
- **Fixed Phrase Vocabulary**: Sunn recognizes phrases that have been enrolled or seeded into the user's personal phrase library. It cannot interpret open-ended conversational speech outside of enrolled phrases and slot-word templates.
- **Consistency Requirement**: The matching relies on Prisma mishearing a person's phrase in a similar way each time. If its transcripts of the same phrase vary a lot, or two phrases come back alike, Sunn picks the wrong one.
- **Ephemeral Cloud Storage on Free Tiers**: On free Hugging Face Docker Spaces, local container storage resets on restart or sleep. Real users' recordings belong on a server with persistent storage, or on a local machine.

---

## 3. Judge-Facing Evaluation Sequence

Judges and challenge mentors can evaluate Sunn either through a deployed instance or via a local dry run.

### Demonstration Flow (3 to 5 Minutes)

| Step | Action | Route | Expected Result |
| :--- | :--- | :--- | :--- |
| **1. Sign Up** | Enter Name, Email, Invite Code (if configured), Password, the language you speak (Hindi or English), and tick consent. | `/signup` | Explicit consent captured; the 51 everyday phrases and starter building blocks are added. |
| **2. Welcome Guide** | Four short steps: welcome, the app's language (only the screen's; the language spoken is in Settings), how Sunn learns, getting ready. | `/app/onboarding` | Explains the tap-to-record interaction and the 3 recordings per phrase. |
| **3. Teach** | Record the 10 quick-start phrases (help, pain, basic needs), 3 times each. Speak opens once all 10 are ready. | `/app/enroll` | Each saved recording fills a dot; a note says when Speak is open. |
| **4. Live Speak** | Tap the central sun button, say an enrolled phrase (e.g. *पानी चाहिए* or *I need help*), tap to stop. | `/app/speak` | The sun's glow follows the voice; Prisma transcribes; the 3 closest phrases are shown, best first ("Maybe" when the match is weak). |
| **5. Confirmation** | Tap the right phrase, or "None of these" to type it. | `/app/speak` | Timbre says the phrase aloud; the recording joins that phrase's examples. |
| **6. Phrase Library** | Search, filter by place (Home, Hospital, Market) or Urgent, add, edit and delete phrases. | `/app/phrases` | Immediate filtering; phrases recorded only in a previous language say "Record again". |
| **7. Settings** | App language, the language you speak, text size, focus outlines, reduced motion, own voice, caregiver contact. | `/app/settings` | Changes apply at once; the caregiver number becomes a wa.me link; account deletion asks first. |
| **8. Progress** | Review counts, the first-suggestion match rate, top phrases and the weekly trend. | `/app/progress` | A weekly trend of how often Prisma alone already got the phrase right; not a medical measure. |

---

## 4. Synthetic Demo Data vs Live Gnani Inference

To protect evaluator budgets and ensure reproducible evaluations even when offline or in noisy environments, Sunn strictly demarcates live inference from synthetic evaluation data:

### 1. Live Gnani Inference (Interactive Mode)
- **Speech Input**: Real microphone audio captured in the browser via WebRTC MediaRecorder.
- **Transcribing**: Audio sent to Gnani Prisma STT API endpoint.
- **Synthesis**: Confirmed phrase sent to Gnani Timbre TTS inference endpoint.
- **Fallback**: If the network is unavailable or API credits are exhausted, the browser's native `window.speechSynthesis` executes automatically with an on-screen notice.

### 2. Synthetic Demo Data (Offline Evaluation Mode)
- **Demo Corpus**: A folder of recordings you make yourself (`data/demo/`, kept out of git; how to record it, and the consent it needs, is in `docs/DEMO_DATA.md`).
- **Provenance Tagging**: Every stored sample carries a strict `speech_source` database tag:
  - `pilot`: A real person with a speech difference who gave informed consent.
  - `simulated`: Someone without a speech difference imitating unclear speech. It shows the pipeline works and says nothing about real users.
  - `torgo`: Recordings from the TORGO database of dysarthric speech (check its licence before using them publicly).
  - `NULL`: Recordings made directly by the user in the live application.
- **Offline Evaluation Script**:
  ```powershell
  uv run scripts/evaluate.py --email demo@example.com --folder data/demo
  ```
  Reports raw Prisma exact-match accuracy, Sunn's top-1 and top-3 accuracy, the effect of the place context, and accuracy with 1 to 3 enrollment recordings, per source. Each held-out recording is sent to Prisma once (cached after), so the first run spends credits. It refuses to run with `GNANI_MOCK` on.

---

## 5. Verified Privacy, Data Flow, and Local Storage Guarantees

What leaves the server, and what stays:

### 1. External Data Flow (What Leaves the Server)
- **Gnani Prisma STT**: Audio recordings of spoken phrases are transmitted to Gnani's API for transcription. Only the audio bytes necessary for transcription are sent.
- **Gnani Timbre TTS**: Confirmed phrase text is sent to Gnani's synthesis endpoint to generate speech audio.
- **Gnani Voice Clone**: Only if the user adds their own voice: that recording is sent once to make the voice, then deleted.
- **No Third-Party Analytics**: No trackers, telemetry, analytics or advertising code in the frontend or backend. The web app does load its fonts from Google Fonts.

### 2. Local Storage and Data Isolation (What Stays Local)
- **Database Storage**: User profiles, phrase texts, slot words, templates, and usage timestamps reside exclusively in the local SQLite database (`DATA_DIR/app.db`).
- **Audio Files**: WAV recordings are stored under `DATA_DIR/users/<user_id>/`; cached Prisma transcripts under `DATA_DIR/cache/prisma/`. The server does not provide any public endpoint to browse or download these recordings.
- **Static File Isolation**: The static web server serves exclusively from `web/dist`. Automated path-traversal regression tests verify that directory escape attempts (`../.env` or `../app.db`) are blocked.
- **Redacted Operational Logging**: Logs are written to `logs/app.log` in JSON Lines format with automated 5 MB rotation. Sensitive credentials, raw passwords, session tokens, audio paths, and full transcripts are sanitized before writing.
- **Account Deletion**: `DELETE /api/me` first deletes the user's recordings, their cached transcripts and the cloned voice on disk, then the user's rows in `users`, `phrases`, `slot_words`, `templates`, `samples` and `uses` in one database transaction. Call counts stay, tied to no one, as does the shared stock-voice cache.

---

## 6. Safe Deployment Dry Run and Verification Commands

Judges and evaluators can verify the entire application locally using standard terminal commands without incurring API costs:

### 1. Local Setup
```powershell
# 1. Install backend dependencies
uv sync

# 2. Build production frontend assets
cd web; npm ci; npm run build; cd ..

# 3. Run the backend tests (every Gnani call faked)
uv run pytest

# 4. Launch single-container server (API + Web on port 7860)
uv run src/server.py --port 7860
```
Open [http://localhost:7860](http://localhost:7860) in a desktop browser. To try it without spending Gnani credits, set `GNANI_MOCK=1` first: Prisma and Timbre answers are then made up, and the server says so at startup.

### 2. Pre-Flight Deployment Dry Run
Verify that the repository contains no untracked secrets, uncommitted changes, or blocked files:
```powershell
uv run scripts/deploy_space.py --check-only
```
Expected output: Lists the tracked deployment files and reports `checks passed: XX files would be uploaded`.

---

## 7. Operational Troubleshooting Guide

| Issue / Error | Likely Root Cause | Verified Resolution |
| :--- | :--- | :--- |
| **Microphone blocked / red icon** | Non-secure origin on mobile, or permission denied in browser | On desktop, use `http://localhost:7860` (treated as secure origin). On mobile, access via HTTPS direct URL. Check browser site permissions to allow microphone access. |
| **502 `gnani_unreachable`** | Gnani didn't answer, or `GNANI_API_KEY` is not set | The API fails safely without crashing. Playback falls back to browser speech synthesis (`window.speechSynthesis`), with an on-screen notice; recognition waits for Prisma. |
| **502 `gnani_rejected`** | Gnani refused the request, for example an invalid key (HTTP 401) | Check the key in the Space's secrets. |
| **403 `invite_required`** | Sign-up attempted without invite code when `DEMO_INVITE_CODE` is set | Enter the designated evaluator invite code in the signup form. |
| **429 `too_many_attempts`** | 5 wrong invite codes from one address, or 5 failed logins for one email, within 15 minutes | Locked for up to 15 minutes; the message says how long. |
| **429 `credit_limit_reached`** | Global `GNANI_CALL_LIMIT` reached | Previously cached phrases continue to play without spending new credits. Local TTS fallback remains active. |
| **404 on page reload** | Reverse proxy misconfiguration or accessing framed HF preview | Always use the direct space address (`https://<space>.hf.space`), which routes unknown paths to `index.html` for client-side routing. |
| **Cold start delay** | Free Hugging Face Space waking from idle pause | The first visit after a pause waits for the container to start; after that it answers normally. |

---

## 8. Final Challenge Submission Checklist

This checklist tracks the final deliverables required for official form submission:

| Deliverable | Description / Location | Status |
| :--- | :--- | :---: |
| **Code Repository** | `https://github.com/ARYANPATEL-BIT/sunn` | **Verified Ready** |
| **Backend Test Suite** | `uv run pytest` passes (counts in docs/AUDIT.md) | **Verified Ready** |
| **Frontend Production Build** | Vite production bundle built without errors (`web/dist/`) | **Verified Ready** |
| **Technical Write-Up** | Comprehensive solution documentation in `docs/WRITEUP.md` | **Verified Ready** |
| **Health Check & Ops** | Live health probe at `/api/health` and `/health` with log rotation | **Verified Ready** |
| **Live Deployment URL** | Direct Space URL: `[placeholder: https://<username>-sunn.hf.space]` | *Manual Team Action* |
| **Evaluator Invite Code** | Passcode for judges: `[placeholder: private code generated for reviewers]` | *Manual Team Action* |
| **3-Minute Demo Video** | Video link (YouTube/Drive): `[placeholder: demo video link]` | *Manual Team Action* |
| **Social Announcements** | LinkedIn and X posts prepared in `docs/POSTS.md` | *Manual Team Action* |
