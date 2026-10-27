---
title: Sunn
sdk: docker
app_port: 7860
pinned: false
short_description: Speech aid for dysarthric speech, Hindi and Indian English
---

# Sunn

Sunn is a speech aid for people whose speech is hard for others, and for speech recognition,
to understand. They say one of their everyday phrases the way they can, and Sunn shows what it
thinks they meant and says it aloud in a clear voice.

Built on Gnani's Prisma (speech to text) and Timbre (text to speech) for the Gnani Great Indian
AI Internship Challenge. Hindi and Indian English.

## The problem

Dysarthria is a speech disorder caused by conditions such as stroke, Parkinson's disease,
cerebral palsy or ALS. Words come out slurred, slow or uneven. Family members often learn to
understand the person, but strangers, nurses and shopkeepers often can't, and general speech
recognition, trained mostly on typical speech, often gets it wrong too. That leaves the person
pointing, writing, or waiting for someone to translate for them.

The people Sunn is for are dysarthric speakers of Hindi or Indian English, and the family
members or caregivers who help them set it up.

## How it works

```mermaid
flowchart LR
    U([Person speaks]) --> B[Web app<br/>React, in the browser]
    B -- "recording, /api/me/recognize" --> S[Sunn server<br/>FastAPI, src/server.py]
    S -- "16 kHz WAV" --> P[Gnani Prisma<br/>speech to text]
    P -- "what it heard" --> S
    S --> M[Matcher, src/matcher.py<br/>compare with this person's<br/>enrollment fingerprints]
    M -- "top 3 phrases" --> B
    B -- "the chosen phrase, /api/speak" --> S
    S -- "phrase text" --> T[Gnani Timbre<br/>text to speech,<br/>or their cloned voice]
    T -- "WAV" --> B
    S <--> D[(SQLite database,<br/>recordings and caches<br/>in DATA_DIR)]
```

1. **Enroll.** The person (or a helper) picks everyday phrases (51 come built in, like पानी
   चाहिए or "I need help") and records each one about 3 times. Sunn sends each recording to
   Prisma and stores what Prisma heard: its *hypothesis*.
2. **Speak.** Later the person says one of those phrases. Prisma transcribes it, and Sunn
   compares that transcript with every stored hypothesis and shows the 3 closest phrases.
3. **Confirm.** The person taps the right one and Timbre says it aloud. The confirmed
   recording joins that phrase's examples, so Sunn learns from use.

### The error fingerprint idea

Sunn doesn't try to correct Prisma or to train a speech model. It uses Prisma's mistakes.

When Prisma mishears a particular person saying a particular phrase, it tends to mishear it
in a similar way each time. Say "पानी चाहिए" comes back as "बानी चाई" again and again. That
consistent wrong transcript is a fingerprint of the phrase in this person's voice. Sunn keeps
the fingerprints from enrollment, and at speaking time it asks which phrase's fingerprints
the new transcript is closest to, instead of whether the transcript is right.

That is why it needs little data: there is no model to train, only a few transcripts to
store. A phrase is usable after about 3 recordings, a new phrase can be added at any time by
recording it, and everything is per person, so one person's patterns never get averaged with
anyone else's. It also means Sunn can only ever pick a phrase the person has enrolled, and it
only works as well as Prisma's mistakes are consistent (see Limitations).

The details, all in `src/matcher.py`:

- Both texts are normalized: Devanagari is transliterated to ITRANS (so Devanagari and
  romanized output compare fairly), lowercased, and reduced to letters, digits and spaces.
- Similarity is normalized Levenshtein similarity, 0–100. A phrase scores as its closest
  fingerprint.
- Small boosts settle near ties: +6 when the phrase is tagged with the place the person
  chose (home, hospital, market), up to +4 for how often they use it, up to +3 for how often
  they use it at this time of day. Together they add at most 13, never enough to beat a
  clearly closer match.
- A best similarity under 60 is flagged as low confidence.
- **Building blocks**: a template like `{item} चाहिए` or `Call {person}` and its slot words
  (पानी, "the nurse") are recorded separately, and Sunn joins their fingerprints. So
  "चाय चाहिए" can be recognized without ever being recorded as a whole.

## How Gnani's APIs are used

All calls go through `src/gnani.py`: a 15 s timeout, one retry after a timeout, a lost
connection or a 5xx, and a row in the `api_calls` table for every request.

- **Prisma speech to text** (`https://api.vachana.ai/stt/v3`, `src/prisma.py`). Every
  recording is converted to 16 kHz mono 16-bit WAV with ffmpeg (bundled in `imageio-ffmpeg`)
  and sent with `language_code` `hi-IN` or `en-IN` (the person's language) and `format`
  `verbatim`. Used twice: at enrollment, where the transcript becomes a fingerprint, and at
  speaking time, where it is matched against them. Sunn never shows Prisma's transcript as the
  answer; it only uses it for matching.
- **Timbre text to speech** (`https://api.vachana.ai/api/v1/tts/inference`, model
  `timbre-v2.5`, `src/speak.py`). Says the chosen phrase with voice Nalini (`hi-IN`) or Kaveri
  (`en-IN`), as a 48 kHz WAV.
- **Voice cloning** (`https://api.vachana.ai/api/v1/tts/voice-clone/embeddings`, then the
  same inference endpoint with model `vachana-vc-v1`). Optional, and only with separate
  consent: from 5–30 s of the person's own speech, Sunn can speak in a voice like theirs. Only Gnani's embedding is kept, never the
  recording.

Every Prisma transcript and Timbre clip is cached on disk under `DATA_DIR/cache/` by a hash
of the audio or text and the full request, so the same request is never paid for twice.

## Features

- Sign-up with consent, optional invite code; sign-in with an httpOnly session cookie
- 51 built-in everyday phrases in Hindi and in English, tagged by place, with "I need help"
  and "I'm in pain" marked urgent
- Enrollment of phrases, about 3 recordings each. Templates and slot words work in the API;
  the web app has no screens for them yet
- Speaking: tap to record, then pick from the top 3 candidates, which Timbre says aloud.
  Optional place context, an urgent badge, and a low-confidence flag
- The person's own cloned voice, if they want it
- Phrase library: search, add, edit, tag and delete phrases
- A caregiver contact, for a ready-made WhatsApp link
- Progress: phrase and recording counts, top-1 hit rate, most used phrases, and a weekly
  trend of how often Prisma got it right without Sunn's help
- Speech in Hindi or Indian English, interface in English or Hindi, switchable at any time
- Accessibility settings (large text, reduced motion), WCAG AA contrast
- Credit protection: a server-wide cap on Gnani calls (`GNANI_CALL_LIMIT`) and a per-account
  daily cap (`DAILY_CALL_CAP_PER_USER`)

## Results

**Not measured yet for this version.** No evaluation has been run on real or demo recordings
of the current matcher, so there are no numbers to report here. Nothing below should be read
as a result until this section links real charts.

How it will be measured (`scripts/evaluate.py`, docs/DEMO_DATA.md): a demo account is
enrolled from a folder of recordings, and recordings held out of enrollment are run through
the same matching. It reports raw Prisma exact-match accuracy, Sunn's top-1 and top-3
accuracy, the effect of the place context, and accuracy with 1, 2 or 3 enrollment recordings
per phrase, overall and separately for each source of speech (`pilot`: a real person who
consented; `torgo`: the TORGO dysarthric speech corpus; `simulated`: imitated unclear speech,
which says nothing about real users). Every chart title states the source and the number of
recordings, and every run is reported, including bad numbers.

<!-- After running scripts/evaluate.py, replace the paragraph above with the real numbers from
results/eval_<account>.csv and link the charts, with their data source:
![Raw Prisma vs Sunn](results/eval_<account>_accuracy.png)
![Context off vs on](results/eval_<account>_context.png)
![Enrollment recordings per phrase](results/eval_<account>_enrollments.png) -->

## Limitations

- **A fixed phrase set.** Sunn picks from phrases the person has enrolled. It can't
  understand new sentences; anything new has to be added and recorded first.
- **It depends on Prisma's mistakes being consistent.** If the same phrase comes back very
  differently each time, or two phrases come back alike, Sunn will pick the wrong one. Short
  phrases and phrases that sound alike are the hardest.
- **It needs the internet.** Every recognition is a Prisma call and every new phrase spoken
  is a Timbre call. Nothing works offline except what's cached.
- **The demo host resets.** The public demo runs on a free Hugging Face Space, which sleeps
  when idle and loses all accounts and recordings whenever it restarts (docs/DEPLOY.md).
- **Not tested with enough people.** See Results.
- **Not a medical device.** Sunn is a communication aid. It doesn't diagnose, treat or
  measure speech, and the progress screen is a usage trend, not a clinical measure. Don't
  rely on it alone in an emergency.

## Privacy and consent

- Sign-up needs explicit consent (`consent_given_at` is stored). Voice cloning needs a second,
  separate consent (`voice_consent_given_at`).
- Recordings are sent to Gnani for transcription. They are stored on the Sunn server under
  `DATA_DIR/users/<id>/`, and no endpoint serves them back.
- Every per-user route takes the user from the session cookie, never from the URL. Another
  person's ids answer 404, and every update and delete is scoped to the signed-in user.
- `DELETE /api/me` deletes the account and everything it made: phrases, building blocks,
  recordings, their cached transcripts, and the cloned voice with everything spoken in it.
  `DELETE /api/me/voice` forgets just the voice. Kept: the stock-voice Timbre cache (phrase
  text in Nalini's or Kaveri's voice, not tied to anyone) and call counts, which are no
  longer tied to the account.
- Logs (`logs/app.log`) hold ids, counts and codes only. Passwords, tokens, emails, audio
  paths, phrase text and transcripts are redacted.
- Passwords are hashed with argon2. Failed logins are limited per email and wrong invite
  codes per IP address.
- Demo data from real people needs their informed consent first, and TORGO's licence must
  be checked before its recordings are used publicly (docs/DEMO_DATA.md).

## Run it locally

Needs [uv](https://docs.astral.sh/uv/) and Node 20.19+ (or 22.12+), on Windows PowerShell:

```powershell
uv sync
Copy-Item .env.example .env   # then fill in GNANI_API_KEY and a JWT_SECRET:
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"

cd web; npm ci; npm run build; cd ..
uv run src/server.py          # the app on http://127.0.0.1:7860, API docs at /api/docs, health at /api/health
```

Desktop browsers treat `localhost` as a secure context, so the microphone works on
http://localhost:7860. All settings are in `.env.example`.

While working on the frontend, run the API and Vite's dev server instead, for hot reload:

```powershell
uv run uvicorn api:app --app-dir src --port 8000   # terminal 1
cd web; npm run dev                                 # terminal 2: http://localhost:5173, proxies /api to :8000
```

On a phone, the microphone needs https. Run `npm run tunnel` in `web/` (needs `cloudflared`:
`winget install Cloudflare.cloudflared`) for a temporary `https://*.trycloudflare.com`
address. Anyone with that address can reach your dev server while it runs, so stop it when
you're done. For LAN https with mkcert, put `cert.pem` and `key.pem` in `web/certs/`.

The web app's design system is in `web/DESIGN.md`.

### Demo data and evaluation

```powershell
uv run scripts/load_demo.py --email demo@example.com --folder data/demo
uv run scripts/evaluate.py --email demo@example.com --folder data/demo
```

How to record and organize the folder, and the consent it needs, is in docs/DEMO_DATA.md.

## Presenter Demo Guide (3 to 5 Minutes)

Sunn includes a built-in Presenter Mode to help demo the app reliably to judges, mentors, and partners.

### 1. Starting the Application
```powershell
# Terminal 1: Backend API (port 8000)
uv run uvicorn api:app --app-dir src --port 8000

# Terminal 2: Web frontend (http://localhost:5173)
cd web; npm run dev
```
Open `http://localhost:5173` in a desktop browser (Chrome, Edge, or Firefox). Desktop localhost is treated as a secure origin, so microphone permissions work without TLS certificates.

### 2. Activating Presenter Mode
- Click the **Demo** pill in the top header, or press **Alt + P** (**Option + P** on macOS).
- The Presenter Cue Bar docks near the top of the screen with step-by-step cues, quick-jump pills, and progress indicators.
- Presenter Mode can be collapsed with the chevron or exited anytime with the close button or **Alt + P**.

### 3. Step-by-Step Demo Journey (Approx. 4 Minutes)
1. **Step 1: Onboarding and Language Setup (0:00 to 0:45)**:
   - Jump to Onboarding (`/app/onboarding`).
   - Explain Sunn's core mission: an assistive communication aid for people whose speech is difficult to understand.
   - Show English / Hindi language toggle and the 3-recording learning principle.
2. **Step 2: Personal Phrase Library (0:45 to 1:30)**:
   - Jump to Phrase Library (`/app/phrases`).
   - Point out everyday phrases, context tags (home, hospital, market), and urgent tags.
   - Point out the demo source badges: `Demo (Pilot)` indicates consented dysarthric speaker data, `Demo (Simulated)` indicates pipeline test data, and untagged phrases represent live user enrollments.
3. **Step 3: Speak, Recognize, and Synthesis (1:30 to 3:00)**:
   - Jump to Speak Screen (`/app/speak`).
   - Select a context (e.g. `Hospital` or `Home`) to show contextual ranking.
   - Tap the Sun to speak or record. Show top candidate ranking with similarity scores.
   - Tap a candidate to confirm and hear clear speech output.
4. **Step 4: Accessibility and Voice Cloning (3:00 to 3:45)**:
   - Jump to Settings (`/app/settings`).
   - Demonstrate accessibility controls: Large Text, Enhanced Focus rings, and Reduced Motion.
   - Explain own-voice cloning with strict separate consent requirements (`voice_consent_given_at`).
5. **Step 5: Transparent Metrics and Privacy (3:45 to 4:30)**:
   - Jump to Progress (`/app/progress`).
   - Clarify the metrics: Sunn measures speech recognition consistency against Gnani raw hypotheses, not clinical recovery.
   - Highlight the atomic account deletion option (`DELETE /me`) that wipes all audio and database records immediately.

### 4. Handling Failures and Fallbacks During Presentations
- **Microphone permission blocked**: The screen displays an inline troubleshoot guide with instructions to allow access in the browser address bar.
- **Speech service exhaustion / offline**: If Gnani Timbre reaches limits or network drops, playback automatically falls back to browser offline speech synthesis (`window.speechSynthesis`), clearly labeled as local browser fallback.
- **Demo data transparency**: Every pre-enrolled phrase displays its origin badge so judges always know whether data is pilot-recorded or simulated.

### Demo and Submission Resources
- **Live Service Dependency Matrix**: `docs/DEMO_MATRIX.md` documents cloud services, cache behavior, and fallback mechanisms.
- **Step-by-Step Demonstration Runbook**: `docs/DEMO_RUNBOOK.md` provides the exact presentation script and timing.
- **Demo Video Recording Plan**: `docs/DEMO_VIDEO_PLAN.md` provides the 3-minute video storyboard and narration text.
- **Challenge Submission Checklist**: `docs/SUBMISSION_CHECKLIST.md` tracks deliverables and manual team actions.
- **Challenge Write-Up**: `docs/WRITEUP.md` provides the problem statement, solution architecture, and differentiators.

## Deploy

One Docker image (`Dockerfile`) serves the API under `/api` and the web app everywhere else
on port 7860. docs/DEPLOY.md has the exact steps for a free Hugging Face Docker Space: the
secrets to add (including `TRUST_PROXY=1` and `DEMO_INVITE_CODE`), how to push with
`scripts/deploy_space.py`, and what to
expect (it sleeps when idle and loses its data on restart).

## Tests

```powershell
uv run pytest
```

Each test runs the API in its own temporary folder, with every Gnani call faked, so the
tests never spend credits or touch `data/`.

The smoke test drives a running server end to end over HTTP: sign-up, enrollment, building
blocks, recognition, confirmation, edits, stats and account deletion. It needs two short
recordings of real speech and makes 2 Prisma calls (`--voice ref.wav` adds a voice clone and
a Timbre call):

```powershell
uv run scripts/smoke_test.py first.wav second.wav                          # http://127.0.0.1:7860/api
uv run scripts/smoke_test.py first.wav second.wav --url https://<you>-sunn.hf.space/api --invite <code>
```

## Challenge Submission

- **Master Submission Package**: [`docs/SUBMISSION_PACKAGE.md`](docs/SUBMISSION_PACKAGE.md) (judge-facing evaluation guide, problem statement, architecture, truthful limits, and troubleshooting).
- **Technical Write-up**: [`docs/WRITEUP.md`](docs/WRITEUP.md) (in-depth solution design, user personas, and pipeline details).
- **Deployment and Dry Run**: [`docs/DEPLOY.md`](docs/DEPLOY.md) (Docker setup, persistent storage comparison, and pre-flight check).
- **Live Demo Runbook**: [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md) (step-by-step evaluator journey).
- **Demo Video Script**: [`docs/DEMO_VIDEO_PLAN.md`](docs/DEMO_VIDEO_PLAN.md) (3-minute shot list and recording plan).

## API

`docs/API.md` is the contract the web app is built against: every route, its body, an
example answer and its error codes. The live version is `/api/docs`.

## Other scripts

- `uv run src/speak.py --text "I need water" --language en`: one Timbre call, saved to
  `results/tts_test.wav`
- `src/correct.py` and `src/eval_correct.py`: the first feasibility test of the fingerprint
  idea, run on Prisma transcripts of TORGO recordings. They read
  `results/prisma_predictions.csv`, which isn't in the repo.


## Contributors

1. Aryan Patel
2. Tuhin Mondal