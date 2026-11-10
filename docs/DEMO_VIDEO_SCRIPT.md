# Sunn: Hackathon Demo Video Script & Walkthrough Runbook

**Project**: Sunn (सुन) - Every Voice Understood  
**Target Video Duration**: 2 minutes 30 seconds to 3 minutes  
**Target Audience**: Hackathon Judges, Speech Accessibility Mentors, and General Public  
**Date**: November 2026  

---

## 1. Video Production Overview

The goal of this video is to demonstrate Sunn's core assistive speech capabilities in a clear, compelling, and human-centered manner. The demonstration highlights the live speech recognition loop, clear voice synthesis, structured trainings with WPM pace tracking, and AI-powered "Easier Ways to Say It" alternative phrasing.

---

## 2. Pre-Recording Technical Checklist

Complete these verification steps before pressing record:

1. **Service Mode Selection**:
   - For Live Recording with real API keys: Verify `.env` has valid `GNANI_STT_API_KEY`, `GNANI_TTS_API_KEY`, and `GROQ_API_KEY`.
   - Run live smoke tests:
     ```bash
     uv run scripts/gnani_live_smoke.py
     uv run scripts/groq_live_smoke.py
     ```
   - For Contingency / Offline Recording: Set `GNANI_MOCK=1` in `.env` or start command to execute zero-cost deterministic simulated speech.
2. **Deterministic Demo State**:
   - Seed the demo account before recording:
     ```bash
     uv run scripts/seed_demo_user.py
     ```
   - Demo Credentials:
     - Email: `evaluator@sunn.app` (or newly created user)
     - Password: `Password123`
3. **Display & Audio Setup**:
   - Recommended Resolution: 1920x1080 (16:9 widescreen) or 1440x900.
   - Browser Zoom: Set browser zoom to 100% or 110% for crisp typography readability.
   - Audio Output: Ensure system audio capture is enabled in your recording software (OBS Studio / QuickTime) so synthesized speech is audible in the recording.
   - Microphone: Use a dedicated headset or USB condenser microphone with minimal background noise.

---

## 3. Timed Shot-by-Shot Video Script

| Time | Screen / Route | Visual Action | Suggested Narration |
| :---: | :--- | :--- | :--- |
| **0:00 - 0:25** | Public Landing (`/`) | Slow scroll through hero, showing the live acoustic waveform blob animating. Hover over mission statement. | "Over ten million people across India live with speech differences, cerebral palsy, stroke recovery, or dysarthria. For them, standard voice assistants fail up to eighty percent of the time, turning everyday requests into frustrating friction. This is Sunn. Sunn is an assistive voice companion engineered to understand atypical speech and vocalize intent clearly across ten Indian languages." |
| **0:25 - 0:45** | Assistive Speak (`/app/speak`) | Click "Start Speaking" or sign in. Arrive on Speak screen. Highlight the tactile orange push button and acoustic canvas blob. | "Here is Sunn's assistive speaking interface. Instead of forcing users into open-vocabulary recognition that misinterprets slurred sounds, Sunn pairs Gnani Prisma speech-to-text with a personalized phonetic matching engine trained on the speaker's everyday phrase bank." |
| **0:45 - 1:15** | Live Recognition & Synthesis | Push the microphone button. Speak a dysarthric-styled phrase (e.g., 'mujhe pani chahiye' or simulated recording). The acoustic visualizer animates. 3 ranked intent cards appear. | "Watch what happens. The user speaks naturally. Sunn captures the acoustic input, analyzes phonetic substitutions, and instantly ranks candidate matches. When the user taps the top card, Sunn vocalizes their exact intent in a clear, dignified voice using Gnani Timbre text-to-speech." |
| **1:15 - 1:35** | Phrase Library (`/app/phrases`) | Navigate to Phrases tab. Show categorized phrases (`home`, `hospital`, `urgent`). Click into a template phrase like '{item} please'. | "Users customize their personal communication bank with everyday phrases, context filters for hospitals or markets, and slot-variable templates like 'I want water' or 'I want tea' for single-tap independence." |
| **1:35 - 2:05** | Trainings Hub & Paced Speaking (`/trainings`) | Open Trainings. Click 'Smooth Speaking' -> 'Easy Starts' -> 'Paced Speaking'. Show the real-time WPM tempo bar as speech is paced. | "Beyond daily communication, Sunn empowers users with sixteen structured speech training lessons. Here in Paced Speaking, users practice rhythm and syllable pacing with real-time Words Per Minute feedback, helping build speech confidence at their own pace." |
| **2:05 - 2:35** | Easier Ways to Say It (`/trainings/easier-ways`) | Navigate to Easier Ways. Show detected tricky sounds. Type 'I need a glass of water'. Click search. Groq-generated alternatives appear. Tap 'Add to Phrases'. | "When specific consonant clusters cause physical fatigue, Sunn's 'Easier Ways' engine detects tricky sounds and leverages Groq Cloud's GPT-OSS 120B model to rewrite phrases into natural, easier-to-pronounce alternatives without changing intent. With one tap, the easier phrase is saved to their library." |
| **2:35 - 2:50** | Settings & Accessibility (`/app/settings`) | Open Settings. Show binary theme toggle, large text, high-contrast focus rings, and emergency caregiver contact. | "Sunn is designed for universal accessibility: WCAG AA contrast, high-contrast focus rings for switch devices, instant reduced motion, and direct WhatsApp links to caregivers for emergency peace of mind." |
| **2:50 - 3:00** | Landing Page Closing (`/`) | Switch language picker to Hindi / Tamil. Return to hero screen. | "With complete localization across ten Indian languages, Sunn bridges the communication gap so that every voice is understood. Thank you." |

---

## 4. Presenter Demo Walkthrough (Alternative Evaluation Mode)

If demonstrating live to evaluators or judges in a hands-on session, use Sunn's built-in **Presenter Demo Mode**:

1. **Activation**:
   - Click the **Demo** button in the header navigation bar, or press keyboard shortcut `Alt + P` (or `Option + P` on macOS).
2. **Step 1: Onboarding Welcome**:
   - Explains Sunn's mission, privacy protections, and dynamic phrase goal setup.
3. **Step 2: Phrase Bank Orientation**:
   - Spotlights the personal phrase library, showing everyday categories and priority badges.
4. **Step 3: Assistive Speak Demonstration**:
   - Anchors directly over the push-to-record button and candidate intent readout cards.
5. **Step 4: Accessibility and Voice Controls**:
   - Highlights large text, high-contrast focus outlines, reduced motion, and voice cloning safeguards.
6. **Step 5: Progress and Practice Metrics**:
   - Shows completed lesson counts, daily practice minutes, and 7-day consistency streaks.
7. **Evaluator Safety Guarantee**:
   - Presenter Demo mode is executed entirely in client-side memory. Stepping forward and backward through the tour produces zero mutations in the database and consumes zero API credits.

---

## 5. Contingency & Fallback Plans

During a live presentation or recording session, follow these contingency procedures if unexpected technical issues arise:

### Scenario A: Microphone Permission Denied or Inaudible
- **Action**: Use a browser with permissions already granted (Chrome / Edge). If running locally, ensure access is over `http://localhost:5173` or `https://`.
- **Backup**: Use the Presenter Demo Mode (`Alt+P`), which simulates the complete interaction visual state without requiring live audio input.

### Scenario B: Gnani or Groq Cloud Service Latency / Unreachable
- **Action**: Switch seamlessly to local mock mode:
  ```bash
  export GNANI_MOCK=1
  ```
- **Result**: The backend returns pre-packaged deterministic transcripts and audio responses within 10ms, allowing the recording or presentation to proceed smoothly without embarrassing loading spinners.

### Scenario C: Accidental Rate Limit Reached
- **Action**: Log in with an email listed in `LIMIT_EXEMPT_EMAILS` (e.g., `evaluator@sunn.app` or `OWNER_EMAIL`).
- **Result**: The account bypasses daily speech limits completely.
