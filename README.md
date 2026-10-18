# Sunn

Speech aid for dysarthric speech, built on Gnani's hosted APIs.

## Setup

```powershell
uv sync
Copy-Item .env.example .env   # then put your GNANI_API_KEY in .env
```

## Personal correction layer

Needs `results/prisma_predictions.csv` (speaker, wav_path, reference, hypothesis) from the feasibility step.
These scripts make no Gnani calls; they only reuse Prisma hypotheses already in that file.

```powershell
# enrollment: show a speaker's phrase bank (first 2 repetitions of each prompt said 3+ times)
uv run src/correct.py --speaker F01

# recognize: top 3 bank phrases for a new Prisma hypothesis (score 0-100, higher = closer)
uv run src/correct.py --speaker F01 --hypothesis "hell me"

# evaluate on the held-out repetitions -> results/correction.csv, results/correction.png
uv run src/eval_correct.py
```

## TTS test

Sends one Hindi text to Gnani Timbre v2.5 (voice Nalini, hi-IN). Audio is cached in
`data/cache/tts/`, so re-running with the same text sends nothing.

```powershell
uv run src/speak.py                          # default text
uv run src/speak.py --text "मुझे पानी चाहिए"  # -> results/tts_test.wav
```

## Backend

A user enrolls phrases by speaking them, then speaks freely and gets the top 3 enrolled
phrases back; the chosen one is spoken with Timbre v2.5. Uploads (webm/ogg from the
browser) are converted to 16 kHz mono WAV with the ffmpeg bundled in `imageio-ffmpeg`.
Data lives in `data/app.db` and `data/users/<user_id>/`; every Prisma and Timbre response
is cached under `data/cache/` by audio/text hash, so the same recording or text is never
sent twice. Default phrases: `data/default_phrases_hi.txt`.

```powershell
# API on all interfaces so a phone on the same Wi-Fi can reach it; docs at http://localhost:8000/docs
uv run uvicorn api:app --app-dir src --host 0.0.0.0 --port 8000

# in a second terminal: create a user, add default phrases, enroll 2 of them, recognize the first
uv run scripts/smoke_test.py first.wav second.wav
```

The smoke test makes 2 Prisma calls (one per enrollment); the recognize step reuses the
first recording's cached transcript.

## Frontend

Vite + React app in `web/` for patients and caregivers: setup with consent, enrollment
(each phrase recorded 3 times; leave any time and it resumes at the first unfinished
phrase), the speak screen, and progress numbers from `/stats`.

```powershell
cd web
npm install
Copy-Item .env.example .env   # VITE_API_URL=/api
npm run dev                   # serves https://localhost:5173 and https://<your-lan-ip>:5173
```

Run the API (see Backend) at the same time. The dev server proxies `/api` to
`http://localhost:8000`, so only port 5173 needs to be reachable from the phone.

### On a phone

1. Connect the phone to the same Wi-Fi as the computer.
2. Open the `Network:` address that `npm run dev` prints, e.g. `https://192.168.1.20:5173`.
3. The certificate is self-signed, so the browser warns once: choose Advanced → Proceed.
   The page has to be https, because phones only allow the microphone on secure pages.
4. Allow the microphone when asked.

If the phone can't connect, allow Node.js through Windows Firewall on private networks.
