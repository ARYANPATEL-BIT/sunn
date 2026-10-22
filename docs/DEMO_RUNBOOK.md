# Final Demonstration Runbook (3 to 5 Minutes)

This runbook provides a reproducible, step-by-step walkthrough for live presentations to judges, mentors, and clinical partners.

## Prerequisites and Local Environment

1. **Backend Server**:
   ```powershell
   uv run uvicorn api:app --app-dir src --port 8000
   ```
2. **Frontend Dev Server**:
   ```powershell
   cd web; npm run dev
   ```
   Open `http://localhost:5173` in a desktop browser (Chrome, Edge, or Firefox).
3. **Presenter Mode Activation**:
   - Click the **Demo** pill in the top navigation header, or press **Alt + P** (**Option + P** on macOS).
   - The Presenter Cue Bar docks near the top of the viewport with step navigation pills and talking points.

---

## 5-Step Live Demonstration Journey

### Step 1: Mission and Onboarding (0:00 to 0:45)
- **Route**: `/app/onboarding` (or Step 1 on the Presenter Bar)
- **Action**: Display the welcome card and demonstrate language selection (Hindi / Indian English).
- **Presenter Script**:
  > "Sunn is an assistive communication assistant built for people with dysarthria, whose speech may be slurred or unclear due to stroke, Parkinson's disease, or cerebral palsy. Instead of attempting to retrain large speech models, Sunn uses Gnani Prisma to capture consistent error fingerprints for everyday phrases."
- **Expected Result**: Language switches cleanly; explains the 3-recording learning principle.
- **Recovery Plan**: If the account already finished onboarding, click Step 1 on the Presenter Bar to jump directly back to the guide.

### Step 2: Personal Phrase Library (0:45 to 1:30)
- **Route**: `/app/phrases` (or Step 2 on the Presenter Bar)
- **Action**: Search for "help", filter by "Hospital", and point out the urgency badges and demo source badges.
- **Presenter Script**:
  > "Users start with 51 common phrases for basic needs, pain, and hospital settings. Preloaded phrases are labeled with provenance badges: Pilot indicates real consented dysarthric speaker data, Simulated indicates pipeline verification data, and untagged phrases represent live user enrollments."
- **Expected Result**: Phrase cards display clear tags (`Demo (Pilot)`, `Urgent`, `Hospital`).
- **Recovery Plan**: If the library is empty, click "Add everyday phrases" to populate the default phrase bank in under one second.

### Step 3: Speak Screen and Context Recognition (1:30 to 3:00)
- **Route**: `/app/speak` (or Step 3 on the Presenter Bar)
- **Action**: Select the `Hospital` context, tap the Sun to record or select a candidate phrase, confirm the selection, and listen to the speech output.
- **Presenter Script**:
  > "In the Speak screen, context selection boosts relevant phrases like pain and medicine. When the speaker speaks unclearly, Gnani Prisma transcribes it, and Sunn ranks the enrolled candidates by phonetic similarity. Tapping a candidate confirms it and speaks it aloud immediately."
- **Expected Result**: Candidate cards appear with similarity rankings. Tapping a candidate triggers Gnani Timbre speech output.
- **Recovery Plan**:
  - *Microphone blocked*: Point out the on-screen troubleshooting instructions.
  - *Gnani TTS unavailable*: The app automatically uses browser speech synthesis fallback (`window.speechSynthesis`) and displays a clear notice.

### Step 4: Accessibility and Voice Controls (3:00 to 3:45)
- **Route**: `/app/settings` (or Step 4 on the Presenter Bar)
- **Action**: Toggle Large Text, Enhanced Focus, and Reduced Motion. Explain own-voice cloning consent.
- **Presenter Script**:
  > "Accessibility is foundational. Sunn includes instant switches for Large Text, high-contrast Enhanced Focus rings, and Reduced Motion for motor sensitivities. Optional voice cloning allows synthesis in the user's pre-injury voice, requiring explicit standalone consent."
- **Expected Result**: The interface typography, focus indicators, and animations adapt immediately.
- **Recovery Plan**: Toggle the settings back and forth to demonstrate instant client-side persistence without page reloads.

### Step 5: Transparent Progress and Privacy Safeguards (3:45 to 4:30)
- **Route**: `/app/progress` (or Step 5 on the Presenter Bar)
- **Action**: Show weekly recognition consistency trends and highlight the complete account deletion cascade.
- **Presenter Script**:
  > "We believe in honest metrics. Sunn measures speech recognition consistency against raw transcripts, not medical recovery. All audio and embeddings are isolated per user. Calling Delete Account immediately purges all audio files, cached transcripts, and database rows in a single atomic operation."
- **Expected Result**: Metrics cards and top phrases display cleanly; deletion confirmation dialog is accessible.
- **Recovery Plan**: Clarify that if progress has no uses recorded yet, the screen displays a helpful empty state guiding the user to speak their first phrase.

---

## Post-Demo Cleanup

1. Press **Alt + P** to exit Presenter Mode.
2. Sign out or delete the temporary demo account via `/app/progress` or `/app/settings`.
