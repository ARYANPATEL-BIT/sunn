# Final Demonstration Runbook (3 to 5 Minutes)

This runbook provides a reproducible, step-by-step walkthrough for live presentations to judges, mentors, and clinical partners.

## Prerequisites and Evaluation Modes

### Mode A: Single-Port Production Server (Recommended for Reviewers)
```powershell
cd web; npm run build; cd ..
uv run src/server.py --port 7860
```
Open `http://localhost:7860` in a desktop browser (Chrome, Edge, or Firefox). Desktop browsers treat localhost as a secure origin, enabling microphone access.

### Mode B: Dual Dev Servers with Hot Reload (For Development)
1. **Backend Server**:
   ```powershell
   uv run uvicorn api:app --app-dir src --port 8000
   ```
2. **Frontend Dev Server**:
   ```powershell
   cd web; npm run dev
   ```
   Open `http://localhost:5173`.

### Evaluator Account Setup and Invite Code
1. Navigate to `/signup`. If `DEMO_INVITE_CODE` is configured on the server, enter the designated evaluator invite code in the demo code field.
2. Enter Name, Email, Password, select language (Hindi or English), and check the consent box.
3. Once registered, click the **Demo** pill in the top header (or press **Alt + P** / **Option + P** on macOS) to activate the Presenter Bar.

---

## 5-Step Live Demonstration Journey

### Step 1: Mission and Onboarding (0:00 to 0:45)
- **Route**: `/app/onboarding` (or Step 1 on the Presenter Bar)
- **Action**: Display the welcome card. Show both languages with the EN / हिं switch in the header, not the guide's own language cards: those also change the language the account speaks, so its recordings stop counting (docs/AUDIT.md).
- **Presenter Script**:
  > "Sunn is an assistive communication assistant built for people with dysarthria, whose speech may be slurred or unclear due to stroke, Parkinson's disease, or cerebral palsy. Instead of retraining speech models, Sunn keeps Gnani Prisma's transcripts of a few recordings of each everyday phrase as its fingerprint, betting that Prisma mishears a person's phrase in a similar way each time."
- **Expected Result**: The screen's language switches; explains the 3-recording learning principle.
- **Recovery Plan**: If the account already finished onboarding, click Step 1 on the Presenter Bar to jump directly back to the guide.

### Step 2: Personal Phrase Library (0:45 to 1:30)
- **Route**: `/app/phrases` (or Step 2 on the Presenter Bar)
- **Action**: Search for "help", filter by "Hospital", and point out the urgency badges and demo source badges.
- **Presenter Script**:
  > "Users start with 51 common phrases for basic needs, pain, and hospital settings. Preloaded phrases are labeled with provenance badges: Pilot marks recordings by a real speaker who consented, TORGO the TORGO research corpus, and Simulated speech someone imitating unclear speech. Phrases without a badge were recorded in the app."
- **Expected Result**: Phrase cards display clear tags (`Demo (Pilot)`, `Urgent`, `Hospital`).
- **Recovery Plan**: If the library is empty, click "Add everyday phrases" to add the 51 everyday phrases.

### Step 3: Speak Screen and Context Recognition (1:30 to 3:00)
- **Route**: `/app/speak` (or Step 3 on the Presenter Bar)
- **Action**: Use an account whose 10 quick-start phrases have 3 recordings each (Speak opens only then; a demo account from `scripts/load_demo.py`, or record them on Teach). Select the `Hospital` context, tap the Sun to record, pick a candidate, and listen to the speech output.
- **Presenter Script**:
  > "In the Speak screen, context selection boosts relevant phrases like pain and medicine. When the speaker speaks unclearly, Gnani Prisma transcribes it, and Sunn ranks the enrolled phrases by how close that transcript is to each phrase's fingerprints. Tapping a candidate confirms it and speaks it aloud immediately."
- **Expected Result**: The three closest phrases appear, best first (no scores are shown). Tapping one triggers Gnani Timbre speech output.
- **Recovery Plan**:
  - *Microphone blocked*: Point out the on-screen troubleshooting instructions.
  - *Gnani TTS unavailable*: The app automatically uses browser speech synthesis fallback (`window.speechSynthesis`) and displays a clear notice.

### Step 4: Accessibility and Voice Controls (3:00 to 3:45)
- **Route**: `/app/settings` (or Step 4 on the Presenter Bar)
- **Action**: Toggle Large Text, Enhanced Focus, and Reduced Motion. Explain own-voice cloning consent.
- **Presenter Script**:
  > "Accessibility is foundational. Sunn includes switches for Large text, High-contrast focus outlines, and Reduced motion. Optional voice cloning can speak in the user's own voice from before their speech changed, from an old voice note, with its own consent."
- **Expected Result**: The interface typography, focus indicators, and animations adapt immediately.
- **Recovery Plan**: Toggle the settings back and forth to demonstrate instant client-side persistence without page reloads.

### Step 5: Transparent Progress and Privacy Safeguards (3:45 to 4:30)
- **Route**: `/app/progress` (or Step 5 on the Presenter Bar)
- **Action**: Show the weekly trend and the account deletion option.
- **Presenter Script**:
  > "We believe in honest metrics. The weekly trend shows how often Prisma's own transcript already matched the confirmed phrase. It is a usage trend, not a medical measure. Each person's audio and voice are theirs alone. Delete Account removes the recordings, cached transcripts and cloned voice, then the account's rows in one database transaction. Only call counts and the shared stock-voice cache stay, tied to no one."
- **Expected Result**: Metrics cards and top phrases display cleanly; deletion confirmation dialog is accessible.
- **Recovery Plan**: Clarify that if progress has no uses recorded yet, the screen displays a helpful empty state guiding the user to speak their first phrase.

---

## Post-Demo Cleanup

1. Press **Alt + P** to exit Presenter Mode.
2. Sign out or delete the temporary demo account via `/app/progress` or `/app/settings`.
