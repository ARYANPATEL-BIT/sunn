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
