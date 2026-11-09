# Sunn Hackathon Demonstration Checklist

This practical guide is designed for the presentation team on demo day to ensure a smooth, confident, and reliable presentation of Sunn.

---

## 1. Before the Demonstration (T-15 Minutes)

- [ ] **Deployment Connectivity**:
  - Open the production URL or local server (`http://localhost:7860`).
  - Verify `GET /health` returns `{"status": "ok"}`.
- [ ] **Microphone Permission**:
  - Ensure the browser has granted microphone access for the domain.
  - Check browser permission icon in the address bar (lock icon -> Permissions -> Microphone -> Allow).
- [ ] **Audio Output & Volume**:
  - Test computer speaker volume to ensure synthesized speech playback is audible to judges.
- [ ] **Environment Verification**:
  - Verify server-side `.env` is loaded with `GNANI_STT_API_KEY`, `GNANI_TTS_API_KEY`, and `GROQ_API_KEY` (if testing live calls).
  - Verify `GNANI_MOCK=1` is set if demonstrating offline fallback without consuming live credits.
- [ ] **Clean Browser State**:
  - Close extraneous tabs and developer tools so no sensitive keys or debug traces are visible on screen.
  - Ensure zoom level is set to 100% or comfortable presentation scale.
- [ ] **Seed Demo Account**:
  - Sign in to the pre-seeded demo account (`demo@example.com`) or create a fresh account to verify default phrase enrollment.

---

## 2. Step-by-Step Demonstration Walkthrough (3-4 Minutes)

### Step 1: Introduction and The Problem (0:00 - 0:45)
- Open the landing page (`/`).
- State Sunn's mission: *"Sunn is an accessibility speech and communication platform for people whose speech is difficult for unfamiliar listeners and standard voice assistants to understand."*
- Highlight the problem: dysarthria, stroke, and motor-speech differences cause everyday communication friction and social isolation.
- Click the interactive audio sample on the landing page to demonstrate acoustic intent recognition.

### Step 2: Presenter Guided Demo Launch (0:45 - 1:15)
- Click the **Demo** button in the header or press `Alt + P` (`Option + P` on macOS).
- Explain that Sunn includes a built-in evaluator guide that navigates through the product journey with zero database pollution.
- Step 1 (Onboarding): Show the 3-recording learning principle and regional language support.

### Step 3: Phrase Library & Contextual Tags (1:15 - 1:45)
- Advance to Step 2 (Phrases).
- Showcase everyday essential phrases, categorized tags (`home`, `hospital`, `market`), and urgent indicators.
- Demonstrate slot-variable templates (e.g. *"I want [water/tea/medicine]"*).
- Point out origin badges: `Demo (Pilot)` and `Demo (TORGO)` to emphasize evaluation transparency.

### Step 4: Assistive Speaking & Intent Synthesis (1:45 - 2:30)
- Advance to Step 3 (Speak).
- Tap the microphone button to simulate or record speech input.
- Show how Sunn aligns the spoken hypothesis to personal phrase fingerprints.
- Tap a candidate card to trigger natural vocalization in Hindi or Indian English.
- Show the visualizer blob dynamically animating to speech audio levels.

### Step 5: Guided Trainings Curriculum & Pace Math (2:30 - 3:15)
- Navigate to `/trainings`.
- Showcase the 4 curriculum categories (`Smooth Speaking`, `Clear Sounds`, `Kids Speaking`, `Everyday Talk`).
- Open a lesson (e.g., `Easy Starts - Paced Practice`) and explain the step progression: Listen & Repeat, Read Aloud, Paced Speaking, and Reflection.
- Explain the pace math engine: real-time Words Per Minute (WPM) calculation providing supportive feedback without judgment.

### Step 6: Tricky Sounds & "Easier Ways" (3:15 - 3:45)
- Open `/trainings/easier-ways`.
- Show how Sunn tracks difficult phonemes from practice attempts and self-ratings.
- Demonstrate the Groq-powered semantic rephrasing engine (`openai/gpt-oss-120b`): entering a sentence with difficult sounds suggests natural, easier-to-pronounce alternatives.
- Click "Add to Phrases" to show single-tap library saving.

### Step 7: Transparent Progress & Account Lifecycle (3:45 - 4:00)
- Open `/progress` to display practice minutes, completed lessons, and weekly streak tracking.
- Open `/settings` to highlight WCAG AA accessibility controls: large text, high-contrast outlines, reduced motion, and complete account data deletion (`DELETE /me/account`).

---

## 3. Contingency and Backup Plans

| Failure Scenario | Immediate Action | Backup Explanation to Judges |
| :--- | :--- | :--- |
| **Microphone Permission Denied** | Use the pre-enrolled phrases or Presenter Demo navigation (`Alt+P`). | *"The browser blocked microphone permissions; we can seamlessly showcase intent synthesis and curriculum flows through the pre-recorded library."* |
| **Internet Interruption or Gnani Outage** | Enable mock mode (`GNANI_MOCK=1`) or demonstrate cached audio. | *"Sunn features automatic local caching and simulated fallback providers so communication aids remain resilient during connectivity drops."* |
| **Groq Cloud API Latency or Rate Limit** | Search known vocabulary on Easier Ways. | *"When the LLM assistant is unreachable, Sunn automatically falls back to local phonetic phrase substitution from the user's verified phrase bank."* |
| **TTS Audio Playback Fails** | Rely on browser speech synthesis fallback (`window.speechSynthesis`). | *"Sunn includes automatic browser-native speech synthesis fallback when cloud TTS services are unavailable."* |
| **Accidental State Corruption** | Click 'Reset Defaults' in Phrase Library or restart Presenter Mode. | *"The app allows resetting default phrases at any time, restoring full operational state."* |

---

## 4. After the Demonstration

- [ ] Close the Presenter Demo overlay (`Alt+P` or exit button).
- [ ] If temporary personal audio was recorded during live testing, navigate to Settings and click **Delete Account** to verify clean data purging.
- [ ] Confirm no API tokens or environment files were left exposed on the presentation machine.
- [ ] Log any judge questions or feedback for the post-hackathon roadmap.
