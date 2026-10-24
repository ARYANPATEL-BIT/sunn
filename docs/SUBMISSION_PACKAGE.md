# Sunn Challenge Submission Package

**Gnani AI's Great Indian AI Internship Challenge**  
**Project**: Sunn (सुन)  
**Submission Category**: Speech AI / Assistive Technology  
**Primary Languages**: Hindi (`hi-IN`) and Indian English (`en-IN`)

---

## 1. Executive Summary and Problem Statement

Sunn is an accessibility speech assistant engineered for individuals with atypical speech patterns caused by dysarthria, stroke, cerebral palsy, Parkinson's disease, or motor-neuron conditions.

### The Speech Challenge
Standard automatic speech recognition (ASR) engines are predominantly trained on neurotypical speech. When presented with dysarthric speech (marked by slurred articulation, variable phonation, or reduced breath control), off-the-shelf recognizers typically exhibit word error rates exceeding 50%. This forces individuals with atypical speech to rely on manual pointing, typing on boards, or continuous translation by family members.

### Sunn's Core Innovation: Acoustic Phonetic Fingerprinting
Sunn does not attempt to repair the general speech recognizer or train large neural models from scratch. Instead, it leverages a clinical observation: **motor-speech dysarthria produces repeatable, consistent articulatory variations for the same speaker**.

1. When a user records an everyday phrase 2 to 3 times during enrollment, Gnani's Prisma STT often misrecognizes the words.
2. Crucially, Prisma tends to produce the **same or similar phonetic misrecognition each time** for that speaker's vocal tract characteristics.
3. Sunn stores those repeatable misrecognitions as an **acoustic phonetic fingerprint** of the intended phrase.
4. When the user speaks in daily life, Sunn matches the incoming hypothesis against their personal phrase fingerprints and active context (Home, Clinic, Market, Urgent), presenting the top 3 candidate phrases.
5. Upon confirmation, the phrase is vocalized clearly using Gnani's Timbre TTS (Nalini in Hindi, Kaveri in English) or the browser's Web Speech API fallback.

---

## 2. Technical Architecture and Stack

| Component | Technology | Role and Implementation Details |
| :--- | :--- | :--- |
| **Frontend** | React 19, Vite, Plain CSS | Responsive single-page application, high-contrast mode, accessible focus targets, WebRTC audio recorder, Web Speech API fallback. |
| **Backend API** | FastAPI, Python 3.13 / 3.14 | RESTful ASGI backend serving endpoints under `/api`, token authentication, audio conversion via `imageio-ffmpeg`. |
| **Speech-to-Text** | Gnani Prisma STT | Transcribes incoming WAV audio samples (16 kHz mono 16-bit PCM). |
| **Text-to-Speech** | Gnani Timbre TTS v2.5 | Synthesizes confirmed phrases aloud (`Nalini` for Hindi, `Kaveri` for Indian English). |
| **Local Speech Fallback** | Browser Web Speech API | Client-side `window.speechSynthesis` provides immediate vocalization if offline or API limits are reached. |
| **Database & Storage** | SQLite (`app.db`), Local Disk | Single-tenant database storage, personal audio samples stored in user directories, zero multi-tenant cloud audio pooling. |
| **Deployment** | Docker, Uvicorn | Single container image serving both API and static frontend on port 7860. |

### Truthful Limitations and Non-Medical Disclaimer
- **Not a Medical Device**: Sunn is a communication assistance tool. It does not diagnose, treat, prevent, or measure speech disorders. The Progress dashboard displays usage and recognition trends, not clinical therapy metrics.
- **Fixed Phrase Vocabulary**: Sunn recognizes phrases that have been enrolled or seeded into the user's personal phrase library. It cannot interpret open-ended conversational speech outside of enrolled phrases and slot-word templates.
- **Acoustic Consistency Requirement**: The matching engine relies on the user making relatively consistent articulatory errors. If speech articulation varies drastically between attempts, recognition confidence will degrade.
- **Ephemeral Cloud Storage on Free Tiers**: On free Hugging Face Docker Spaces, local container storage resets on restart or sleep. Real patient recordings must only be deployed on persistent VPS volumes or tested locally.

---

## 3. Judge-Facing Evaluation Sequence

Judges and challenge mentors can evaluate Sunn either through a deployed instance or via a local dry run.

### Demonstration Flow (3 to 5 Minutes)

| Step | Action | Route | Expected Result |
| :--- | :--- | :--- | :--- |
| **1. Sign Up** | Enter Name, Email, Password, Language (Hindi or English), and Invite Code (if configured). | `/signup` | Explicit consent captured; account initialized with starter building blocks. |
| **2. Onboarding** | Follow 4-step wizard: Language selection, consent confirmation, phrase category, and practice recording. | `/app/onboarding` | User calibrates microphone and learns the tap-to-record interaction. |
| **3. Live Speak** | Tap the central sun button, articulate an enrolled phrase (e.g. *पानी चाहिए* or *I need help*), tap to stop. | `/app/speak` | Waveform visualizer animates; Prisma transcribes; top 3 matching candidates are ranked with confidence indicators. |
| **4. Confirmation** | Tap the confirmed phrase card. | `/app/speak` | Timbre TTS synthesizes the confirmed phrase aloud; sample joins the phrase's acoustic profile. |
| **5. Phrase Library** | Filter by context (Home, Clinic, Market, Urgent), add custom phrase, test slot substitution. | `/app/phrases` | Immediate phrase filtering; slot-word substitution (e.g. *चाय चाहिए* vs *पानी चाहिए*). |
| **6. Settings** | Toggle high-contrast theme, enter caregiver contact info, test emergency WhatsApp link. | `/app/settings` | Contrast updates immediately; wa.me link formats with country code; data erasure controls visible. |
| **7. Progress** | Review confirmed recognition trends and top-used phrases. | `/app/progress` | Displays usage analytics and raw Prisma similarity trends without diagnostic claims. |

---

## 4. Synthetic Demo Data vs Live Gnani Inference

To protect evaluator budgets and ensure reproducible evaluations even when offline or in noisy environments, Sunn strictly demarcates live inference from synthetic evaluation data:

### 1. Live Gnani Inference (Interactive Mode)
- **Speech Input**: Real microphone audio captured in the browser via WebRTC MediaRecorder.
- **Transcribing**: Audio sent to Gnani Prisma STT API endpoint.
- **Synthesis**: Confirmed phrase sent to Gnani Timbre TTS inference endpoint.
- **Fallback**: If the network is unavailable or API credits are exhausted, the browser's native `window.speechSynthesis` executes automatically with an on-screen notice.

### 2. Synthetic Demo Data (Offline Evaluation Mode)
- **Demo Corpus**: Located in `data/demo/`, containing pre-recorded WAV samples with known transcripts.
- **Provenance Tagging**: Every stored sample carries a strict `speech_source` database tag:
  - `pilot`: Recordings from consented dysarthric pilot participants.
  - `simulated`: Synthetically generated dysarthric speech patterns with controlled articulatory noise.
  - `torgo`: Consented research samples from the TORGO acoustic dysarthria database.
  - `NULL`: Recordings made directly by the user in the live application.
- **Offline Evaluation Script**:
  ```powershell
  uv run scripts/evaluate.py --email demo@example.com --folder data/demo
  ```
  Evaluates top-1 and top-3 accuracy, acoustic distance thresholds, and context filtering without consuming live Gnani credits.
