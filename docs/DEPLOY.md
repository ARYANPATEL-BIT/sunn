# Deploying Sunn

Sunn ships as one Docker image (`Dockerfile` at the repo root): it builds the web app with
Node, installs the backend with uv, and runs `src/server.py`, which serves the API under
`/api` and the web app everywhere else, on port 7860. These steps put it on a free Hugging
Face Docker Space. Commands are for Windows PowerShell, from the repo root.

## Settings

Everything comes from environment variables. Locally they live in `.env` (copy
`.env.example`); on the Space they are its secrets and variables.

| name | needed | what it does |
| - | - | - |
| `GNANI_API_KEY` | yes, secret | the Gnani API key |
| `JWT_SECRET` | yes, secret | signs session cookies. Make a long random one: `uv run python -c "import secrets; print(secrets.token_urlsafe(48))"`. Changing it signs everyone out |
| `DEMO_INVITE_CODE` | yes on a public Space, secret | sign-up needs this code. Make it long and random too (see TRUST_PROXY below), and give it only to the people who should try the demo |
| `TRUST_PROXY` | `1` on the Space, `0` locally | see below |
| `GNANI_CALL_LIMIT` | no (default 4000) | Gnani calls the whole server may send; past it, new ones are refused |
| `DAILY_CALL_CAP_PER_USER` | no (default 60) | Gnani calls one account may send per day (UTC). Cached answers don't count |
| `OWNER_EMAIL` | no | the account that may read `GET /api/me/usage` |
| `DATA_DIR` | no (default `data`) | where the database, recordings and caches go |

## Hosting Options Comparison

| Option | Cost | HTTPS / Mic Support | Data Persistence | Best Used For |
| - | - | - | - | - |
| **Hugging Face Docker Space** | Free | Yes (Native HTTPS direct URL) | Ephemeral on free tier (resets on restart) | Public challenge submission and mentor review |
| **Local Secure Tunnel** (`cloudflared`) | Free | Yes (`*.trycloudflare.com` HTTPS) | 100% persistent (`data/app.db` on host disk) | Live evaluator demos from developer laptop |
| **Self-Hosted VPS** (Docker + Volume) | Low / Paid | Yes (via Caddy, Nginx, or Let's Encrypt) | 100% persistent (`-v data:/home/user/app/data`) | Long-running pilot programs and care centers |

### Storage Persistence Trade-offs

1. **Free Hugging Face Space**: The container filesystem is ephemeral. Reboots, idle sleep (after 48 hours), or redeployments wipe `data/` (SQLite database, user recordings, and cached TTS audio). To preserve demo accounts, run `scripts/load_demo.py` after a restart, or enable Hugging Face persistent disk in Space settings.
2. **Local Tunnel**: All writes persist directly into your local `data/` directory. Zero data loss across reboots. Requires keeping your development computer awake and connected to the internet during demonstration.
3. **Container Volumes**: When deploying to any Docker VPS or container host, always mount a persistent volume to `/home/user/app/data` to ensure user profiles and speech fingerprints survive container restarts.

### Why TRUST_PROXY is on for Hugging Face and off locally

Sign-up allows 5 wrong invite codes per IP address per 15 minutes. On a Space, the app never
talks to browsers directly: every request arrives through Hugging Face's proxy, so the
connection always comes from the proxy's address. Without `TRUST_PROXY`, all users share that
one address, and one person typing 5 wrong codes locks sign-up for everyone.

With `TRUST_PROXY=1`, the app takes the client's address from the `X-Forwarded-For` header
instead: its left-most entry, the client as the proxy saw it. `src/server.py` also starts
uvicorn with proxy headers on, so it sees the original `https` scheme.

Locally there is no proxy, so leave it off: anyone could send their own `X-Forwarded-For`
header and pick whatever address they like. With it off, uvicorn ignores proxy headers
too.

One thing I couldn't check: whether Hugging Face's proxy replaces an incoming
`X-Forwarded-For` or adds to it. If it adds to it, a client can put a made-up address in
front and dodge the 5-tries limit. That's why the invite code should be long and random:
then guessing it is hopeless even without the limit. Logins are limited per email, not per
address, so the proxy doesn't affect them.

## First deploy

1. Make a free **write** token at https://huggingface.co/settings/tokens and sign in with it
   once. The token is saved on this machine, so later deploys don't ask again:

   ```powershell
   uv run hf auth login
   ```
2. Open https://huggingface.co/new-space. Pick a name (say `sunn`), choose **Docker** as the
   SDK with the **Blank** template, and the free **CPU basic** hardware. Make it **Public**, so
   judges can open it without an account. Create it.
3. In the Space, open **Settings → Variables and secrets** and add:
   - **New secret**: `GNANI_API_KEY`, `JWT_SECRET`, `DEMO_INVITE_CODE`
   - **New variable**: `TRUST_PROXY` = `1`, `GNANI_CALL_LIMIT`, `DAILY_CALL_CAP_PER_USER`, and
     optionally `OWNER_EMAIL`

   Secrets and variables reach the container as environment variables when it runs. Nothing
   secret is needed while the image builds.
4. Deploy (replace `<you>` with your Hugging Face username):

   ```powershell
   uv run scripts/deploy_space.py --space <you>/sunn
   ```

## Every later deploy

Commit what you want deployed, then run the script again:

```powershell
uv run scripts/deploy_space.py --space <you>/sunn
```

A new file only goes up once it's committed; the script doesn't warn about untracked files.

### What the script does

It uploads the last commit's tracked files (`git ls-tree HEAD`), as they are in git, through
the Hugging Face API, with the commit message `deploy <short sha>`. Nothing else goes up: no
history, nothing untracked or ignored. It goes through the API instead of `git push` because
Hugging Face rejects git pushes that have binary files anywhere in their history.

It refuses to deploy, and lists the offending paths, when:

- the working tree has uncommitted changes to tracked files, so the Space always runs
  exactly a commit;
- a tracked file matches `.env*`, `data/`, `logs/`, `web/certs/`, `web/reference/` or
  `*.db`. The two exceptions are tracked on purpose, as in `.gitignore`: `.env.example`
  (placeholders only) and `data/default_phrases_*.txt` (the image needs them);
- a file contains the `GNANI_API_KEY` or `JWT_SECRET` value from your local `.env` (or, if
  it's not there, from the environment).

To see what would be uploaded without uploading anything:

```powershell
uv run scripts/deploy_space.py --check-only
```

The front matter at the top of `README.md` (`sdk: docker`, `app_port: 7860`) is what Hugging
Face reads as the Space's settings, so the Space's `README.md` is replaced by the repo's on
every deploy. The Space rebuilds on every upload; follow it in the **Logs** tab. It is ready
when the log shows `Uvicorn running on http://0.0.0.0:7860`. Files deleted from the repo stay
on the Space until you delete them in its **Files** tab.

## Open it

Use the Space's direct address, `https://<you>-sunn.hf.space` (also under **⋮ → Embed this
Space → Direct URL**), and share that one, not the `huggingface.co/spaces/...` page. That page
shows the app inside a frame from another site. Browsers don't send the `SameSite=Lax`
session cookie inside such a frame, so signing in won't stick there, and the frame may not
get microphone access either. On the direct address the app is its own https site, and the
Secure session cookie works as it does locally.

Check it with the smoke test (two short wavs of speech; this makes 2 Prisma calls):

```powershell
$env:DEMO_INVITE_CODE = "<the code>"
uv run scripts/smoke_test.py first.wav second.wav --url https://<you>-sunn.hf.space/api
```

## What to expect from a free Space

- **It sleeps.** A free CPU Space pauses after 48 hours without visitors. The next visitor
  wakes it, which takes a while (the container starts again).
- **Data resets.** The Space's disk is wiped whenever the container restarts: after it wakes
  from sleep, after every upload, and when Hugging Face restarts it. Every account,
  recording and cached Gnani answer is gone. Load the demo account again afterwards
  (`scripts/load_demo.py --url https://<you>-sunn.hf.space/api`, docs/DEMO_DATA.md). Since
  the cache is gone too, each reload sends one Prisma call per enrollment recording, and
  those count against the demo account's daily cap. Hugging Face sells persistent storage;
  this setup doesn't use it.
- **Credits.** Every non-cached Prisma, Timbre and voice clone call spends Gnani credit.
  `GNANI_CALL_LIMIT` caps the whole server and `DAILY_CALL_CAP_PER_USER` each account;
  both answer 429 once used up (`credit_limit_reached`, `daily_cap_reached`).

## Run the same image locally

With Docker Desktop running:

```powershell
docker build -t sunn .
docker run --rm -p 7860:7860 --env-file .env -e TRUST_PROXY=0 sunn
```

Then open http://localhost:7860 (desktop browsers treat localhost as a secure context, so the
microphone and the Secure cookie both work), or run the smoke test against
`http://127.0.0.1:7860/api`. Data stays inside the container and is gone when it stops; add
`-v "${PWD}\data:/home/user/app/data"` to keep it in your `data/` folder instead.

Without Docker: `cd web; npm ci; npm run build; cd ..` then `uv run src/server.py` serves the
same thing on http://127.0.0.1:7860.
