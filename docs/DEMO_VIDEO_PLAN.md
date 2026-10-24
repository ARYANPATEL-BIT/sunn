# Demonstration Video Plan and Recording Script

This document provides a production-ready recording script and screen capture plan for creating the official 3-minute Sunn challenge demonstration video.

## Video Overview and Timing

- **Target Duration**: 3 minutes (180 seconds)
- **Target Resolution**: 1920x1080 (16:9), 30 or 60 fps
- **Audio Setup**: Clear narration microphone, system audio capture for speech synthesis playback
- **Theme**: High-contrast dark theme (SeaLight background)

---

## Shot-by-Shot Storyboard and Script

### Scene 1: The Problem and Mission (0:00 to 0:30)
- **Visual**: Landing page (`/`) showing the title, tagline, and animated SeaLight shader.
- **Narration**:
  > "For millions of people living with stroke, Parkinson's disease, or cerebral palsy, speech becomes motorically difficult and slurred. Standard speech recognition tools often fail because they are trained on typical speech. Sunn is an assistive speech companion designed specifically for Indian languages, starting with Hindi and Indian English."
- **Screen Action**: Scroll smoothly down landing page to show "Under the hood" pipeline cards (Speech -> Prisma -> Personal Layer -> Timbre).

### Scene 2: Onboarding and Linguistic Choice (0:30 to 0:55)
- **Visual**: First-time user onboarding (`/app/onboarding`).
- **Narration**:
  > "Setup is fast and respectful. The user selects their language, Hindi or English, and learns how Sunn personalizes to their voice. Instead of retraining massive models, Sunn learns that when a speaker's pronunciation causes Prisma to mishear, that error is consistent. We treat that error as a unique phrase fingerprint."
- **Screen Action**: Toggle between Hindi and English cards. Click through to the Speak screen.

### Scene 3: Everyday Phrase Library and Provenance (0:55 to 1:25)
- **Visual**: Phrase Library screen (`/app/phrases`).
- **Narration**:
  > "Sunn comes pre-loaded with 51 common phrases covering emergency needs, pain, food, and family. Every phrase can be customized with place contexts and urgency flags. Notice our provenance badges: Pilot indicates real consented speaker recordings, Simulated indicates pipeline verification takes, and untagged phrases represent live user enrollments."
- **Screen Action**: Filter by "Hospital", show "I'm in pain" with Urgent tag, and tap the listen button to hear the audio preview.

### Scene 4: Live Speak Screen, Context Boost, and Synthesis (1:25 to 2:15)
- **Visual**: Speak Screen (`/app/speak`).
- **Narration**:
  > "Here is the core Speak experience. Selecting Hospital context automatically prioritizes phrases like medicine or assistance. When the user taps the Sun and speaks unclearly, Gnani Prisma transcribes it, and Sunn ranks the three closest matching candidates. Tapping the phrase confirms the intent, adds to the learning history, and speaks it aloud immediately through Gnani Timbre."
- **Screen Action**: Select "Hospital", tap Sun, show candidate ranking card with similarity scores, tap top candidate, hear speech synthesis aloud.

### Scene 5: Accessibility and Ethical Voice Controls (2:15 to 2:40)
- **Visual**: Settings screen (`/app/settings`).
- **Narration**:
  > "Accessibility is deeply integrated. Users can activate Large Text for low-vision support, Enhanced Focus rings for motor navigation, and Reduced Motion. For users who want their own voice back, Sunn supports voice cloning, requiring explicit, recorded consent. If the cloud speech service is ever unreachable, Sunn automatically falls back to browser offline speech synthesis."
- **Screen Action**: Toggle Large Text and Enhanced Focus. Point out the own-voice consent toggle.

### Scene 6: Transparent Progress and Conclusion (2:40 to 3:00)
- **Visual**: Progress screen (`/app/progress`).
- **Narration**:
  > "Sunn tracks recognition consistency over time, not medical recovery. All recordings remain strictly isolated to the user, and our account deletion cascades all files and database records atomically. Sunn makes Indian voice AI accessible, personal, and dependable. Thank you."
- **Screen Action**: Show progress consistency card, scroll to Danger Zone ("Delete account"), and fade out on the Sunn wordmark.

---

## Technical Recording Checklist

- [ ] Clear browser cache or use an incognito window with `DEMO_INVITE_CODE` ready if required.
- [ ] Confirm `GNANI_API_KEY` is loaded and `.env` has valid credentials.
- [ ] Ensure system output volume is set so screen recorder captures Timbre TTS playback clearly.
- [ ] Verify presenter mode toggle (`Alt + P`) works cleanly for quick navigation if recording in one continuous take.
- [ ] Ensure no personal email addresses, API keys, or private files are visible during browser recording.
- [ ] Export video as MP4 with H.264 video codec and AAC audio codec.

---

## Feature Status for Presenters and Evaluators

| Feature in Video | Implementation Status | Data Source Used in Demo |
| :--- | :--- | :--- |
| **Prisma STT & Timbre TTS** | **Implemented** | Live Gnani API endpoints |
| **Acoustic Fingerprinting** | **Implemented** | Personal SQLite matching algorithm (`src/matcher.py`) |
| **Web Speech API Fallback** | **Implemented** | Client-side `window.speechSynthesis` |
| **Atypical Speech Samples** | **Synthetic / Consented** | Pre-recorded demo corpus (`data/demo/`) labeled `pilot` or `simulated` |
| **Voice Cloning Consent** | **Implemented / Experimental** | Gnani Voice Clone API (`vachana-vc-v1`), requires explicit audio consent |
| **Progress Metrics** | **Implemented** | Usage history and Prisma string distance trends (non-clinical) |
