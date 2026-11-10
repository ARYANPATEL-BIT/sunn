# Sunn: Hackathon Submission Guide & Pitch Dossier

**Project**: Sunn (सुन) - Every Voice Understood  
**Event**: Gnani AI - The Great Indian AI Challenge  
**Repository**: https://github.com/ARYANPATEL-BIT/sunn  
**Track / Theme**: Assistive AI, Speech & Accessibility  
**Date**: November 2026  

---

## 1. Executive Summary & Elevator Pitch

### The One-Sentence Pitch
Sunn is an assistive speech communication platform and personalized vocal bridge that empowers individuals with dysarthria, speech differences, and motor variations to be understood clearly in their everyday lives across 10 Indian regional languages.

### The Problem
Over 10 million people in India live with speech impairments resulting from cerebral palsy, Parkinson's disease, stroke, traumatic brain injuries, or vocal cord differences. Standard commercial voice assistants and automatic speech recognition (ASR) systems are trained on neurotypical speech data. For an individual with atypical articulation, slurred consonants, or breathy phonation, existing speech engines fail up to 80% of the time. This causes deep communicative frustration, social isolation, and complete reliance on family members to translate routine requests.

### The Solution
Sunn combines:
1. **Assistive Phonetic Speech Recognition**: Leverages Gnani Prisma v2.5 ASR combined with an intelligent phonetic distance matching engine to understand dysarthric speech against user-enrolled reference phrases.
2. **Clear Intent Vocalization**: Synthesizes recognized thoughts into fluent, clear speech using Gnani Timbre v2.5 Text-to-Speech (TTS) or custom cloned voiceprints.
3. **Structured Practice Curriculum**: A 16-lesson interactive training curriculum with real-time Words Per Minute (WPM) pace feedback.
4. **Adaptive Phrasing ("Easier Ways to Say It")**: Automatically detects tricky phonemes and uses Groq Cloud LLM (`openai/gpt-oss-120b`) to rewrite difficult sentences into phonetically simpler alternatives while preserving full meaning.
5. **Pan-Indian Linguistic Accessibility**: 10 Indian languages localized with 100% string key parity.

---

## 2. Key Differentiators & Technical Innovation

Why Sunn succeeds where general-purpose voice assistants fail:

1. **Phonetic Matching Engine vs. Generic ASR**:
   - Generic voice assistants attempt open-vocabulary transcription, which fails catastrophically on atypical phonetic substitutions (e.g., swapping `p` for `b` or dropping `h` sounds).
   - Sunn uses Gnani Prisma to capture the raw acoustic hypothesis, then applies localized Levenshtein distance and phonetic transposition rules against the speaker's personalized phrase bank.
2. **Groq LLM Contextual Reasoning Judge**:
   - When phonetic scores are close, Sunn consults Groq Cloud LLM (`openai/gpt-oss-120b`). The LLM evaluates the hypothesis alongside user situational context (location, time of day, recent phrases spoken) to select the most probable intent via strict JSON output validation.
3. **Adaptive "Easier Ways" Engine**:
   - Speech practice often causes fatigue when users struggle with difficult consonant clusters. Sunn analyzes the speaker's actual practice attempts to identify their specific tricky sounds, then leverages Groq LLM to rewrite phrases using easier-to-pronounce synonyms.
4. **Child Privacy Protection**:
   - Pediatric speech practice in the "Kids Speaking" category strictly avoids persisting speech transcripts to disk or database, protecting young users.
5. **Universal WCAG AA Design**:
   - Hardware-inspired listening device UI featuring high-contrast focus rings (3px solid), large text scaling (125%), full keyboard navigation, and an instant Reduced Motion toggle.

---

## 3. Implemented Capabilities vs. PRD Scope

Sunn has delivered and verified all core capabilities required for real-world assistive operation:

| Capability | What Has Been Built & Verified | Demonstration Method |
| :--- | :--- | :--- |
| **Speech Recognition** | Gnani Prisma v2.5 integration with 16kHz WAV audio capture and phonetic ranking. | Live microphone speak on `/app/speak` or automated mock in e2e tests. |
| **Voice Synthesis** | Gnani Timbre v2.5 TTS with stock regional voices (`Nalini`, `Kaveri`) and voice cloning. | Tap-to-speak intent cards vocalizing synthesized audio in browser. |
| **Phrase Bank** | Custom phrase enrollment, slot-variable templates (`{item} please`), and priority tags. | Add, edit, filter, and record samples on `/app/phrases`. |
| **Training Curriculum** | 16 lessons across 4 categories (Smooth Speaking, Clear Sounds, Kids Speaking, Everyday). | Step-by-step interactive lesson player on `/trainings`. |
| **Paced Speaking (WPM)**| Dynamic pace calculation comparing spoken words-per-minute against targets. | Interactive paced speaking step with real-time visual progress bar. |
| **Tricky Sounds Detection** | Algorithmic aggregator analyzing misrecognitions, practice ratings, and reflections. | Tricky sounds summary cards on `/trainings` and `/trainings/easier-ways`. |
| **Easier Ways to Say It** | Groq Cloud semantic phrase rewriting avoiding specific tricky phonemes. | Live phrase search and 1-tap library addition on `/trainings/easier-ways`. |
| **10-Language UI** | 10 Indian languages (English, Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, Punjabi). | Instant header language selector with 100% string key parity. |
| **Accessibility Suite** | Large text, high-contrast focus outlines, reduced motion, and full keyboard navigation. | Toggles in `/app/settings` and header theme switcher. |
| **Presenter Demo Mode** | Zero-mutation 5-step evaluator tour docking cleanly at viewport top (`Alt+P`). | Header "Demo" button triggering guided spotlight walk. |

---

## 4. Suggested Hackathon Submission Form Responses

### Project Title
Sunn (सुन) - Every Voice Understood

### Tagline / One-Liner
An assistive AI communication companion empowering individuals with dysarthric and motor-speech differences to communicate with confidence across 10 Indian languages.

### Problem Statement (150 words)
Commercial voice assistants and speech-to-text systems fail people with atypical speech patterns (dysarthria, cerebral palsy, Parkinson's disease, post-stroke recovery). When standard ASR engines reject slurred, breathy, or imprecise articulations, speakers face daily communicative friction, social isolation, and loss of independence. In multilingual India, this barrier is amplified by regional accents and dialect variations. Families often must act as full-time interpreters for routine requests. Existing clinical therapy is often expensive and inaccessible outside hospital settings. There is an urgent need for an affordable, private, localized assistive voice bridge that learns how an individual speaks, vocalizes their intent clearly, and offers compassionate, self-paced speech practice.

### Technical Architecture & AI Integration (200 words)
Sunn is built as a unified single-container application combining a FastAPI Python backend and a React 19 frontend:
1. **Speech-to-Text**: Gnani Prisma v2.5 ASR processes 16kHz linear PCM audio streams captured via Web Audio API.
2. **Phonetic Matching Engine**: An algorithmic Levenshtein and phonetic alignment layer maps ASR hypotheses against user-enrolled reference phrases and slot-variable templates.
3. **LLM Disambiguation Judge**: When phonetic candidate confidence is borderline, Groq Cloud (`openai/gpt-oss-120b`) evaluates situational context (location, time of day, recent phrases) using strict JSON output formatting.
4. **Speech Synthesis**: Gnani Timbre v2.5 TTS vocalizes confirmed intents using natural regional voices or user-enrolled custom voice embeddings (`vachana-vc-v1`).
5. **Adaptive Phrasing ("Easier Ways")**: Groq LLM analyzes detected tricky consonant clusters and suggests natural, conversational alternatives that avoid difficult sounds while safeguarding urgent medical phrases.
6. **Data Storage & Privacy**: SQLite database with strict tenant isolation (`WHERE user_id = ?`), local audio partitioning, and cascading account deletion.

### Social Impact & Accessibility (150 words)
Sunn directly advances digital accessibility for underserved communities across India. By supporting 10 Indian regional languages (English, Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, Punjabi), Sunn ensures non-English speakers have equal access to assistive technology. Features like slot-variable templates and emergency WhatsApp caregiver links restore communicative autonomy in urgent contexts (hospitals, markets, transit). All interfaces adhere to WCAG 2.1 AA standards, including high-contrast focus rings, scalable typography, screen-reader navigation, and instant reduced motion toggles. Strict child privacy protections in pediatric training modules ensure safe practice for young children.

### What's Next for Sunn
1. Expanding native acoustic models to additional regional languages (Tamil, Telugu, Bengali) as provider acoustic pipelines mature.
2. Lightweight on-device offline models for remote, low-connectivity rural health centers.
3. Secure speech-language pathologist (SLP) progress dashboard for clinical home exercise monitoring.

---

## 5. Visual Evidence and Screenshot Checklist

Ensure these screenshots (already captured in `docs/screenshots/`) are submitted with the hackathon entry:

### Desktop Landscape Showcase
1. `docs/screenshots/landscape/landing-desktop.png`: Public landing hero with acoustic visualizer blob.
2. `docs/screenshots/landscape/speak-desktop.png`: Active listening interface with microphone and candidate cards.
3. `docs/screenshots/landscape/candidates-desktop.png`: Ranked intent candidates matched to personal phrase library.
4. `docs/screenshots/landscape/phrase-library-desktop.png`: Personal phrase bank with context tags and slot templates.
5. `docs/screenshots/landscape/training-curriculum-desktop.png`: 4 training categories and course syllabus.
6. `docs/screenshots/landscape/paced-speaking-desktop.png`: Paced speaking lesson step with real-time WPM tempo tracking.
7. `docs/screenshots/landscape/easier-ways-desktop.png`: Easier Ways phrase search with Groq alternative suggestions.
8. `docs/screenshots/landscape/progress-desktop.png`: Progress dashboard with 7-day practice streaks.
9. `docs/screenshots/landscape/presenter-demo-desktop.png`: 5-step evaluator presenter demo tour overlay.

### Mobile Portrait Showcase
1. `docs/screenshots/portrait/landing-mobile.png`: Mobile landing experience.
2. `docs/screenshots/portrait/speak-mobile.png`: Mobile touch-first speak screen.
3. `docs/screenshots/portrait/candidate-matches-mobile.png`: Touch-friendly intent cards.
4. `docs/screenshots/portrait/lesson-player-mobile.png`: Mobile lesson player with synchronized audio.
5. `docs/screenshots/portrait/presenter-demo-mobile.png`: Mobile presenter mode walkthrough.

---

## 6. Truthfulness and Disclosure Guidelines

When presenting or submitting Sunn, strictly adhere to these factual claims:

### What to State Accurately
- Sunn is an assistive communication aid and personal practice companion.
- All 10 Indian languages feature 100% translated interface strings verified by automated key parity tests.
- Native speech recognition and synthesis natively target Hindi (`hi-IN`) and Indian English (`en-IN`), with other regional scripts safely falling back to compatible acoustic models.
- Groq Cloud LLM (`openai/gpt-oss-120b`) is utilized for semantic alternative phrasing and contextual disambiguation.
- Development and automated testing utilize mock fixtures (`GNANI_MOCK=1`) to conserve API credits.

### What NOT to Claim
- Do NOT claim that Sunn diagnoses, treats, or cures medical conditions (aphasia, apraxia, dysarthria).
- Do NOT claim full clinical certification or regulatory approval as a medical device.
- Do NOT claim that all 10 languages possess native acoustic speech recognition models.
- Do NOT invent clinical trial statistics or user satisfaction percentages without external documentation.
