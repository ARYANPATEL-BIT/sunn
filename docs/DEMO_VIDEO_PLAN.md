# Demonstration Video Plan and Recording Script

This document provides a production-ready recording script and screen capture plan for creating the official 3-minute Sunn challenge demonstration video.

## Video Overview and Timing

- **Target Duration**: 3 minutes (180 seconds)
- **Target Resolution**: 1920x1080 (16:9), 30 or 60 fps
- **Audio Setup**: Clear narration microphone, system audio capture for speech synthesis playback
- **Theme**: Dark theme (SeaLight background)

---

## Shot-by-Shot Storyboard and Script

### Scene 1: The Problem and Mission (0:00 to 0:30)
- **Visual**: Landing page (`/`) showing the title, tagline, and animated SeaLight shader.
- **Narration**:
  > "For many people living with stroke, Parkinson's disease, or cerebral palsy, speech becomes motorically difficult and slurred. Standard speech recognition tools often fail because they are trained on typical speech. Sunn is an assistive speech companion designed specifically for Indian languages, starting with Hindi and Indian English."
- **Screen Action**: Scroll smoothly down landing page to show "Under the hood" pipeline cards (Speech -> Prisma -> Personal Layer -> Timbre).

### Scene 2: Onboarding and Linguistic Choice (0:30 to 0:55)
- **Visual**: First-time user onboarding (`/app/onboarding`).
- **Narration**:
  > "Setup is fast and respectful. The user selects their language, Hindi or English, and learns how Sunn personalizes to their voice. Instead of retraining models, Sunn bets that when Prisma mishears a person's phrase, it mishears it in a similar way each time. Sunn keeps that transcript as the phrase's fingerprint."
- **Screen Action**: Toggle between the Hindi and English cards (they change only the screen's language). Click through to the Speak screen.

### Scene 3: Everyday Phrase Library and Provenance (0:55 to 1:25)
- **Visual**: Phrase Library screen (`/app/phrases`).
- **Narration**:
  > "Sunn comes pre-loaded with 51 common phrases covering emergency needs, pain, food, and family. Every phrase can be customized with place contexts and urgency flags. Notice the source badges: Pilot marks recordings by a real speaker who consented, TORGO the TORGO research corpus, and Simulated speech someone imitating unclear speech. Phrases without a badge were recorded in the app."
- **Screen Action**: Filter by "Hospital", show "I'm in pain" with Urgent tag, and tap the listen button to hear the audio preview.

### Scene 4: Live Speak Screen, Context Boost, and Synthesis (1:25 to 2:15)
- **Visual**: Speak Screen (`/app/speak`).
- **Narration**:
  > "Here is the core Speak experience. Selecting Hospital gives a small boost to phrases tagged for the hospital, like medicine. When the user taps the Sun and speaks unclearly, Gnani Prisma transcribes it, and Sunn ranks the three closest matching candidates. Tapping the phrase confirms the intent, adds to the learning history, and speaks it aloud immediately through Gnani Timbre."
- **Screen Action**: Use a demo account whose 10 quick-start phrases are recorded (Speak opens only then). Select "Hospital", tap Sun, show the three candidates (best first; no scores are shown), tap the top one, hear it spoken aloud.

### Scene 5: Accessibility and Ethical Voice Controls (2:15 to 2:40)
- **Visual**: Settings screen (`/app/settings`).
- **Narration**:
  > "Accessibility is deeply integrated. Users can turn on Large text, High-contrast focus outlines for keyboard and switch users, and Reduced motion. For users who want their own voice back, Sunn can clone it from a short recording, with its own consent. If Timbre can't be reached, the browser's own speech synthesis says the phrase instead."
- **Screen Action**: Toggle Large text and the focus outlines. Point out the own-voice upload and its consent box.

### Scene 6: Transparent Progress and Conclusion (2:40 to 3:00)
- **Visual**: Progress screen (`/app/progress`).
- **Narration**:
  > "The weekly trend shows how often Prisma already understood a phrase without Sunn's help. It is a usage trend, not a medical measure. Each person's recordings are theirs alone, and deleting the account deletes its phrases, recordings and cloned voice. Sunn makes Indian voice AI accessible and personal. Thank you."
- **Screen Action**: Show progress consistency card, scroll to Danger Zone ("Delete account"), and fade out on the Sunn wordmark.

---

## Technical Recording Checklist

- [ ] Clear browser cache or use an incognito window.
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
| **Error fingerprints (Prisma transcripts)** | **Implemented** | Per-person matching of transcripts (`src/matcher.py`) |
| **Web Speech API Fallback** | **Implemented** | Client-side `window.speechSynthesis` |
| **Demo recordings** | **Only if you record them** | A folder you record (`data/demo/`, kept out of git, docs/DEMO_DATA.md), labeled `pilot`, `torgo` or `simulated` |
| **Voice Cloning Consent** | **Implemented** | Gnani Voice Clone API (`vachana-vc-v1`), with its own consent; upload in Settings |
| **Progress Metrics** | **Implemented** | Usage history and Prisma string distance trends (non-clinical) |
