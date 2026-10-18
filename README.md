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
same 50 everyday phrases, same groups).

### Accounts

No third-party auth. Passwords (8+ characters) are hashed with argon2. A session is a JWT
signed with `JWT_SECRET`, in an httpOnly, Secure, SameSite=Lax cookie that lasts 30 days.

- `POST /auth/signup` `{name, email, password, language, consent: true}`: refused without consent; sets the cookie
- `POST /auth/login` `{email, password}`: sets the cookie. A wrong email and a wrong password get the same answer; after 5 failures for one email within 15 minutes, that email is locked out for the rest of the window (in memory, so a restart clears it)
- `POST /auth/logout`: clears the cookie
- `GET /auth/me`: the signed-in user, or 401

Every per-user route is under `/me/...` and takes the user from the session cookie, never
from the URL, so nobody can reach another person's recordings by changing an id:
`/me/phrases`, `/me/phrases/default`, `/me/enroll`, `/me/recognize`, `/me/confirm`,
`/me/stats`. `/speak` also needs a session. `DELETE /me` deletes the account, its phrases, its
recordings and their cached Prisma transcripts.

```powershell
# API on this machine; the web app reaches it through Vite's proxy. Docs at http://localhost:8000/docs
uv run uvicorn api:app --app-dir src --port 8000

# in a second terminal: sign up, add default phrases, enroll 2 of them, recognize the first
uv run scripts/smoke_test.py first.wav second.wav            # --language en for an English user
```

The smoke test makes 2 Prisma calls (one per enrollment); the recognize step reuses the
first recording's cached transcript.

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

### https, without warnings

Browsers only allow the microphone on https pages, so the dev server uses a certificate from
[mkcert](https://github.com/FiloSottile/mkcert), whose local CA your machine trusts. Once per
machine, then whenever your LAN address changes:

```powershell
winget install FiloSottile.mkcert
mkcert -install                       # trust mkcert's local CA (once)
cd web
mkdir certs
mkcert -cert-file certs/cert.pem -key-file certs/key.pem localhost 127.0.0.1 ::1 <your-lan-ip>
```

`web/certs/` is gitignored. `npm run dev` refuses to start without it.

```powershell
cd web
npm install
npm run dev        # https://localhost:5173 and https://<your-lan-ip>:5173
```

Run the API (see Backend) at the same time. The app only calls relative `/api/*`, which Vite
proxies to `http://localhost:8000`, so the browser talks to one https origin and the login
cookie just works.

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
