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
- **Action**: Display the welcome card and the language step, which changes only the screen's language (the language spoken is in Settings).
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

### Step 6: Trainings, Lesson Player and Easier Ways (Optional Extension: 4:30 to 5:30)
- **Route**: `/app/trainings` (browse courses) -> `/app/trainings/courses/easy-starts` -> `/app/trainings/lessons/easy-starts-1`
- **Action**: Walk through Easy Starts Lesson 1 (Breath and a gentle start). Demonstrate the Listen & Repeat step with pre-synthesized audio, the Speak With Me pacing bar, and open the Easier Ways tool (`/app/trainings/easier-ways`) for "पानी चाहिए".
- **Presenter Script**:
  > "Sunn Trainings provides structured, clinically informed speaking practice across four categories: Easy Starts, Everyday Words, Speech Clarity, and Kids Fun. In Easy Starts Lesson 1, users practice gentle vocal onset with vowel sounds. When a sound feels difficult, the Easier Ways assistant suggests simpler phonetic alternatives while preserving urgency and communicative intent."
- **Expected Result**: The lesson steps advance smoothly; ungenerated audio falls back cleanly to synthetic timing; Easier Ways presents simpler alternatives with one-click addition to the phrase library.
- **Recovery Plan**: If network is offline, the lesson player continues with local timer pacing, and Easier Ways serves pre-curated alternatives from `alternatives.json`.

---

## Live API Credit Budget & Real-Time Monitoring

Sunn is configured to preserve the majority of the ~5,000 Gnani credit budget for presentation:

1. **Credit Ceilings**:
   - `GNANI_CALL_LIMIT=4000`: Hard stop protecting the final 1,000 credit demo buffer.
   - `DAILY_CALL_CAP_PER_USER=60`: Prevents presenter account runaway during rehearsals.
   - `TRAINING_CHECKS_PER_DAY=20`: Limits live STT scoring checks per user per day.
2. **Real-Time Usage Monitoring**:
   - The owner account (`OWNER_EMAIL`) can query `GET /api/me/usage` to inspect live call counts and cache hit ratios.
   - Inspect SQLite call records:
     ```powershell
     uv run python -c "import db; print(db.row('SELECT COUNT(*) as live FROM api_calls WHERE cached = 0'))"
     ```
3. **Emergency Fallback Matrix**:

| Component | Failure Condition | Automatic Platform Response | Presenter Talking Point |
| :--- | :--- | :--- | :--- |
| **Gnani Prisma STT** | Network timeout or quota error | Falls back to cached fingerprints and client notice | "Sunn handles connectivity drops gracefully without interrupting user intent." |
| **Gnani Timbre TTS** | Provider 500 or unreachable | Plays audio via browser `window.speechSynthesis` | "Sunn includes instant browser speech fallback so the user is never left without a voice." |
| **Groq AI Judge** | Rate limit or API error | Retains local phonetic matcher ranking without delay | "AI assists when confident, but local deterministic matching always guarantees speed." |
| **Lesson Audio** | Missing 404 audio file | Visual rhythmic highlighting via synthetic timer | "The curriculum supports audio-free practice with visual pacing bars." |

---

## Post-Demo Cleanup

1. Press **Alt + P** to exit Presenter Mode.
2. Sign out or delete the temporary demo account via `/app/progress` or `/app/settings`.
