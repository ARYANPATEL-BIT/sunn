# Sunn

Speech aid for dysarthric speech, built on Gnani's hosted APIs.

## Setup

```powershell
uv sync
Copy-Item .env.example .env   # then put your GNANI_API_KEY in .env, and a JWT_SECRET:
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`JWT_SECRET` signs the login session cookie. Keep it out of git; changing it signs everyone out.

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

Sends one text to Gnani Timbre v2.5: voice Nalini (hi-IN) for Hindi, Kaveri (en-IN) for
English. Audio is cached in `data/cache/tts/`, so re-running with the same text sends nothing.

```powershell
uv run src/speak.py                                        # default Hindi text
uv run src/speak.py --text "मुझे पानी चाहिए"                # -> results/tts_test.wav
uv run src/speak.py --text "I need water" --language en
```

## Backend

A user signs up, enrolls phrases by speaking them, then speaks freely and gets the top 3
enrolled phrases back; the chosen one is spoken with Timbre v2.5. Uploads (webm/ogg from the
browser) are converted to 16 kHz mono WAV with the ffmpeg bundled in `imageio-ffmpeg`.
Data lives in `data/app.db` and `data/users/<user_id>/`; every Prisma and Timbre response
is cached under `data/cache/` by audio/text hash (language included), so the same request is
never sent twice.

Each user speaks Hindi or English (`language` is `hi` or `en`, chosen at sign-up). Prisma gets
`hi-IN` or `en-IN` (Indian English), Timbre gets `hi-IN` + Nalini or `en-IN` + Kaveri, and the
default phrases come from `data/default_phrases_hi.txt` or `data/default_phrases_en.txt` (the
same 51 everyday phrases, same groups).

### Accounts

No third-party auth. Passwords (8+ characters) are hashed with argon2. A session is a JWT
signed with `JWT_SECRET`, in an httpOnly, Secure, SameSite=Lax cookie that lasts 30 days.

- `POST /auth/signup` `{name, email, password, language, consent: true}`: refused without consent; sets the cookie
- `POST /auth/login` `{email, password}`: sets the cookie. A wrong email and a wrong password get the same answer; after 5 failures for one email within 15 minutes, that email is locked out for the rest of the window (in memory, so a restart clears it)
- `POST /auth/logout`: clears the cookie
- `GET /auth/me`: the signed-in user, or 401

Every per-user route is under `/me/...` and takes the user from the session cookie, never
from the URL or the body, so nobody can reach another person's data by changing an id: an id
that isn't yours answers 404, the same as one that doesn't exist. `/speak` also needs a session.

### Endpoints

Every request and response body is a model in `src/schemas.py`, so `/docs` is the live contract;
`docs/API.md` is the short version, grouped by screen. Recordings are form uploads in a field
named `audio`; everything else is JSON. Every error is `{error, message}`, where `error` is a
code the app can word (`no_speech`, `invalid_input`, `not_found`…).

**Account**

- `PATCH /me` `{use_own_voice, caregiver_name, caregiver_phone}`, any of them. `caregiver_phone`
  is digits with the country code (`919876543210`; spaces, dashes and `+` are dropped), ready
  for a `https://wa.me/<phone>` link. `use_own_voice` needs a recorded voice
- `DELETE /me`: deletes the account and everything it made (see Privacy), and clears the cookie
- `POST /me/voice` (form: `audio`, `consent=true`): clones the user's voice with Gnani's voice
  clone embeddings. Refused without consent. The docs ask for 5–30 s of clear speech, so a
  recording outside that is refused (`audio_too_short` / `audio_too_long`). Only the embedding
  is kept; `use_own_voice` stays off until `PATCH /me` turns it on
- `DELETE /me/voice`: forgets the embedding and everything spoken in it; `use_own_voice` goes off
- `/auth/me` and the account routes return `has_own_voice` and `use_own_voice`, never the embedding

**Phrases**

- `GET /me/phrases`: each with `contexts`, `urgent`, `enrolled` (enrollment recordings),
  `sample_count` (enrollments and confirmed recognitions) and `last_used_at`
- `POST /me/phrases` `{text}`, `POST /me/phrases/default`
- `PATCH /me/phrases/{id}` `{text, contexts, urgent}`, any of them. `contexts` is a list of
  `home`, `hospital`, `market`, `any`
- `DELETE /me/phrases/{id}`: with its samples, their recordings and its uses
- `POST /me/enroll` (form: `phrase_id`, `audio`), `DELETE /me/samples/{id}`

Default phrases get contexts from their group in the phrase file: basic needs → home and
hospital, pain and health → hospital, food and drink and family → home, the rest → any.
मदद चाहिए / I need help and दर्द हो रहा है / I'm in pain are marked urgent.

**Building blocks**: a template like `{item} चाहिए` or `Call {person}` has one slot
(`item`, `person` or `place`) at its start or end. Its fixed part (`चाहिए`, `Call`) and each
slot word (`पानी`, `the nurse`) are recorded on their own, 3 times like phrases.

- `GET` / `POST {slot, text}` / `DELETE /me/slot-words[/{id}]`, `POST /me/slot-words/{id}/enroll` (form: `audio`)
- `GET` / `POST {text}` / `DELETE /me/templates[/{id}]`, `POST /me/templates/{id}/enroll` (form: `audio`)

New users start with items पानी, दवाई, खाना, चाय, कंबल, people बेटे, बेटी, डॉक्टर, नर्स and
the templates `{item} चाहिए`, `{person} को बुलाओ`. English users get water, my medicine, food,
tea, a blanket, my son, my daughter, the doctor, the nurse, `I need {item}` and `Call {person}`.

**Speaking**

- `POST /me/recognize` (form: `audio`, optional `context`): the top 3 candidates. Each has
  `score` and its `parts`, `urgent` and `composed`, explained below
- `POST /me/confirm` `{sample_id}` plus one of `phrase_id`, `new_text`, or a composed
  candidate's `template_id` and `slot_word_id`. Adds the recording to that phrase's samples and
  logs one use. Confirming a composed candidate makes it a real phrase
- `POST /speak` `{text}`: the user's cloned voice when `use_own_voice` is on, else Nalini or Kaveri

A candidate's score is `similarity + context + freq + time`, all in `parts`:

- `similarity`: 0–100, the closest of the phrase's samples to what Prisma heard
- `context`: `CONTEXT_BOOST` (6) if the phrase is tagged with the `context` sent
- `freq`: `FREQ_BOOST` (4) × the phrase's uses as a share of the most used phrase's
- `time`: `TIME_BOOST` (3) × the same, counting only uses in this time of day (morning 5–12h,
  afternoon 12–17h, evening 17–21h, night; the server's local time)

The boosts are at the top of `src/matcher.py`. They add at most 13, so they settle near ties
and never beat a clearly closer match. `low_confidence` looks at the best similarity only.

Composed candidates: every template × slot word of its slot. Their fingerprints are each slot
word recording's Prisma hypothesis joined to each fixed part recording's, in the template's
word order, matched like a phrase's samples. They come back with `composed: true`,
`phrase_id: null`, `template_id` and `slot_word_id`. When the composed text is already a phrase
(पानी + चाहिए = पानी चाहिए), the fingerprints count for that phrase instead and it comes back
as the phrase.

**Progress**

- `GET /me/stats`: totals (`phrases`, `samples`, `recognitions`, `confirmed`, top-1 hit rate),
  `top_phrases` (the 5 most used) and `clear_without_help_by_week`: for each of the last 8 weeks,
  the share of confirmed recognitions whose raw Prisma hypothesis was already within 90 of 100
  of the phrase. A rough trend of how often Prisma understood without the personal layer, not a
  medical measure
- `GET /me/usage`: Gnani calls sent and cached by kind, against the limit. Only for the
  account whose email is `OWNER_EMAIL` in `.env`

### Gnani calls, limits and errors

Every Prisma, Timbre and clone call goes through `src/gnani.py`: a 15 s timeout and one retry
after a timeout, a lost connection or a 5xx. Each call, sent or answered from the cache, is a row
in `api_calls` (kind, cached, audio seconds). Once `GNANI_CALL_LIMIT` (in `.env`, default 4000)
calls have been sent, new ones are refused; cached answers still work. Uploads are refused over
10 MB, and phrase recordings outside 0.3–15 s.

| code | status | meaning |
| - | - | - |
| `gnani_unreachable` | 502 | Gnani didn't answer, or failed twice |
| `gnani_rejected` | 502 | Gnani refused the request |
| `credit_limit_reached` | 429 | `GNANI_CALL_LIMIT` is used up |
| `audio_too_short`, `audio_too_long` | 400 | outside the length limits; the body has `seconds` |
| `file_too_large` | 413 | over 10 MB |
| `bad_audio` | 400 | ffmpeg couldn't read the file |
| `no_speech` | 422 | Prisma heard nothing; nothing is stored |

All the codes are in `docs/API.md`.

### Privacy

`DELETE /me` removes the user's phrases, slot words, templates, samples, uses, every
recording with its cached Prisma transcript, and the cloned voice with everything spoken in it
(all in `data/users/<id>/`). Files go first, so if one can't be removed the account is still
there to try again. Two things are kept because they aren't anyone's data: the stock-voice
Timbre cache (`data/cache/tts/`, phrase text spoken by Nalini or Kaveri, shared by everyone who
says it) and `api_calls` (counts with no user).

`logs/app.log` is one JSON line per request, Gnani call and refusal: ids, paths, status codes,
error codes and timings. Never audio, phrase text, transcripts, emails, passwords or tokens.

### Running

```powershell
# API on this machine; the web app reaches it through Vite's proxy. Docs at http://localhost:8000/docs
uv run uvicorn api:app --app-dir src --port 8000

# in a second terminal: sign up, enroll phrases and building blocks, recognize, confirm, edit,
# read the stats, then delete the account
uv run scripts/smoke_test.py first.wav second.wav            # --language en for an English user
uv run scripts/smoke_test.py first.wav second.wav --voice me.wav   # also clone a voice (5-30 s)
```

The smoke test makes 2 Prisma calls (one per wav); every later step reuses those cached
transcripts. `--voice` adds one clone call and one Timbre call.

An existing `data/app.db` gains the new columns and tables when the API starts. Phrases that
already existed get contexts `any` and aren't urgent, and older accounts have no building blocks
(they're added at sign-up).

### Tests

```powershell
uv run pytest
```

Each test runs the API in its own temporary folder (its own database, recordings and caches),
and every Gnani call is faked, so the tests never use credits or touch `data/`.

## Frontend

Vite + React app in `web/`, plain CSS, react-router-dom for pages, lucide-react for icons.
The design system is `web/DESIGN.md`.

- `/` landing, `/login`, `/signup`
- `/app/enroll` (each phrase recorded 3 times, resumes at the first unfinished phrase),
  `/app/speak` (tap the sun, tap again to stop, then choose the phrase to say it aloud) and
  `/app/progress` (numbers, and deleting the account)
- `/app/*` needs a session: without one it goes to `/login?next=<that page>`, and signing in
  comes back to it. Signing up loads the default phrases and goes to `/app/enroll`
- The interface is in English or Hindi (`web/src/i18n/`), toggled with EN / हिं. That is
  separate from the language a user speaks, which is set at sign-up

The background is one WebGL shader (`web/src/SeaLight.jsx`). It drops to a still CSS version
without WebGL, and to a single frozen frame with reduced motion.

### Local development and HTTPS

Desktop browsers treat `http://localhost` as a secure context, so microphone input works out of the box without certificates:

```bash
cd web
npm install
npm run dev        # http://localhost:5173
```

Run the backend API at the same time (`uv run uvicorn api:app --app-dir src --port 8000`). The web app calls `/api/*`, which Vite proxies to `http://localhost:8000`, so the browser stays on one origin and cookies work seamlessly.

For physical mobile testing on local Wi-Fi without cloud tunnels, create trusted local certificates with [mkcert](https://github.com/FiloSottile/mkcert):

```bash
mkcert -install                       # trust mkcert local CA (once per machine)
cd web
mkdir -p certs
mkcert -cert-file certs/cert.pem -key-file certs/key.pem localhost 127.0.0.1 ::1 <your-lan-ip>
npm run dev        # https://localhost:5173 and https://<your-lan-ip>:5173
```

### On a phone

The phone doesn't trust your computer's mkcert CA, so the LAN address would show a warning
there. Use a Cloudflare quick tunnel instead, which gives a real https address:

1. Install `cloudflared` once: `winget install Cloudflare.cloudflared`
2. Run the API and `npm run dev` as above.
3. In a third terminal: `cd web` then `npm run tunnel`. It prints an address like
   `https://some-words.trycloudflare.com`.
4. Open that address on the phone (any network), sign in, and allow the microphone.

The address changes every time the tunnel starts, and anyone with it can reach your dev
server while it runs, so stop the tunnel (Ctrl+C) when you're done.

### Contrast

Text must pass WCAG AA against the brightest pixel the light can put behind it, not the
average. The shader tone-maps the sky's luminance under a ceiling (`CEILING` in
`web/src/SeaLight.jsx`), and each page sets the light intensity and a sky veil over it in
`web/src/App.jsx` (`SEA`). Checked by computing the brightest possible pixel (any field color
at the ceiling, grain at +3%) for each page: secondary text (mist) is at worst 4.6:1 on the
landing, 6.0:1 on login/signup, 6.7:1 or more in the app; primary text is 7.5:1 or more
everywhere. Raising the ceiling or the grain needs that check again.

## Demonstration Sequence

Follow this sequence to demonstrate Sunn end to end:

1. **Sign Up & First-Time Onboarding:**
   - Open `http://localhost:5173/signup`.
   - Create an account with name, email, password, and preferred language (Hindi or English).
   - Review the 4-step onboarding wizard introducing everyday phrases, pronunciation learning, and communication workflow.
   - Click "Add everyday phrases" to seed starter vocabulary, then proceed.

2. **Teach Phrases (Enrollment):**
   - On `/app/enroll`, record 3 spoken samples for a phrase using the sun button.
   - Listen to recorded audio playback before saving.
   - Once at least one phrase has 3 samples, proceed to `/app/speak`.

3. **Speak & Recognition:**
   - On `/app/speak`, select a context (Home, Hospital, Market, or Any).
   - Tap the sun, speak, and tap again to finish.
   - View the recognized hypothesis and ranked phrase candidates.
   - Tap a candidate to confirm and speak it aloud via speech synthesis.

4. **Phrase Library Management:**
   - On `/app/phrases`, search saved phrases and filter by context or urgency.
   - Add a custom phrase, edit existing phrase contexts, or toggle urgency tags.

5. **Settings, Accessibility & Progress:**
   - On `/app/settings`, toggle large text, reduced motion, or enhanced focus indicators.
   - Configure caregiver contact information for quick WhatsApp messaging.
   - On `/app/progress`, review communication usage trends and top phrases.

## External Services and Offline Boundaries

- **Gnani Prisma STT & Timbre TTS:** Required for live speech-to-text transcription and text-to-speech audio synthesis. All successful responses are cached under `data/cache/` by audio and text hash, allowing repeated demonstration of cached phrases without consuming external API credits.
- **Offline Fallback:** If `GNANI_API_KEY` is not configured, the application surfaces clear localized errors (`error.gnani`) instead of crashing.
- **Medical Disclaimer:** Sunn is a communication assistance tool and does not provide medical diagnosis, clinical speech therapy, or health claims.
