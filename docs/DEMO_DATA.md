# Demo data

A demo account is an ordinary Sunn account whose phrases were taught from a folder of
recordings instead of through the app. `scripts/load_demo.py` loads it through the normal API
(real Prisma calls, cached), and `scripts/evaluate.py` tests it on recordings held out of
enrollment. Every recording keeps a `source`, and the API returns it (`sources` in
`GET /api/me/phrases`), so the app can say where the speech came from.

## Sources

| source | what it is | what it can show |
| - | - | - |
| `pilot` | a real person, with dysarthria or another speech difference, who gave consent (below) | the only one that says anything about real users, and only about that person |
| `torgo` | the TORGO database of dysarthric speech (University of Toronto) | real dysarthric speech, but English, read prompts, and a licence to check first (below) |
| `simulated` | someone without a speech difference imitating unclear speech | that the pipeline works end to end. It is not dysarthric speech, and results on it say nothing about how Sunn works for the people it is for. Always label it as simulated |

## Record and organize the folder

Keep the folder out of git: `data/demo/` is ignored (all of `data/` is, apart from the
default phrase lists). Never commit real people's recordings.

```
data/demo/
  manifest.csv
  water-1.wav
  water-2.wav
  water-3.wav
  water-test-1.wav
  pain-1.wav
  ...
```

`manifest.csv`, UTF-8, one row per recording:

```csv
phrase,file,kind,source
पानी चाहिए,water-1.wav,enroll,pilot
पानी चाहिए,water-2.wav,enroll,pilot
पानी चाहिए,water-3.wav,enroll,pilot
पानी चाहिए,water-test-1.wav,test,pilot
दर्द हो रहा है,pain-1.wav,enroll,simulated
```

- `phrase`: exactly as it should appear in the app. Use the default phrases' wording
  (`data/default_phrases_hi.txt`, `data/default_phrases_en.txt`) where you can: those come
  with contexts (home, hospital…) and urgency, which the context evaluation needs. Any other
  text becomes a new phrase with context `any`.
- `file`: relative to the folder. Any format ffmpeg reads (wav, mp3, m4a, webm…), 0.3 to 15
  seconds, one phrase per file, with a little silence at both ends.
- `kind`: `enroll` recordings are taught to the account, in the order listed. `test`
  recordings are never uploaded; only `scripts/evaluate.py` uses them. A recording can't be
  both (the loader checks by content, not by name).
- `source`: `pilot`, `torgo` or `simulated`.

For results that mean something:

- 3 enroll recordings per phrase (the app's goal), and at least 1 or 2 test recordings.
- Record the test recordings in a different session from the enroll ones (another day if
  possible). Takes from one sitting sound more alike than real use does, so they flatter the
  results.
- Record in the room and on the device the person would really use, and don't redo takes
  because they sound unclear. Unclear takes are the whole point.
- Every phrase with test recordings needs at least one enroll recording, in the account's
  language.

## Load it

The loader signs up the account, or signs in if it exists. It adds the default phrases, then
enrolls every `enroll` row. It checks the whole manifest before it sends anything, stops at
the first refused recording, and carries on from there when run again.

For the evaluation, load into a local server: it writes to your `data/`, which
`scripts/evaluate.py` reads.

```powershell
# terminal 1: the app, on http://127.0.0.1:7860 (build web/ first for the screens; the API works without it)
uv run src/server.py

# terminal 2
$env:DEMO_PASSWORD = "<a password for the demo account>"
uv run scripts/load_demo.py --email demo@example.com --folder data/demo            # --language en for English phrases
uv run scripts/evaluate.py --email demo@example.com --folder data/demo
```

Each new enroll recording is one Prisma call for the demo account, so it counts against
`ENROLL_DAILY_LIMIT` (default 40 in a rolling 24 hours). For a bigger folder, list the demo
account in `LIMIT_EXEMPT_EMAILS` (or make it `OWNER_EMAIL`) while you load, or load over several
days: the loader stops at the limit and picks up where it left off.

Load with `GNANI_MOCK` off. In mock mode every recording gets a made-up transcript, so the demo
account's fingerprints would be made up too (`scripts/evaluate.py` refuses to run in mock mode).

The 10 quick-start phrases have to be in the manifest, 3 recordings each, for the account's
Speak screen to open (`web/src/quickstart.js` lists them): in Hindi मदद चाहिए, दर्द हो रहा है,
पानी चाहिए, बाथरूम जाना है, दवाई दे दो, डॉक्टर को बुलाओ, सांस लेने में तकलीफ़ है, भूख लगी है, ठंड
लग रही है, मुझे उठा दो; in English I need help, I'm in pain, I need water, I need the bathroom,
Give me my medicine, Call the doctor, I can't breathe properly, I'm hungry, I feel cold, Help me
sit up.

To put the same account on the deployed Space, run the loader again with
`--url https://<you>-sunn.hf.space/api`. The Space loses all data whenever it restarts
(docs/DEPLOY.md), so do it again after every restart.

## What the evaluation reports

See the top of `scripts/evaluate.py`. In short: raw Prisma exact match, Sunn top-1 and top-3,
the same with the context set, and accuracy with 1, 2 or 3 enroll recordings per phrase,
overall and per source. Every test row is counted: a recording Prisma heard nothing in counts
as a miss, as it would in the app. `results/eval_<account>.csv` is the summary and
`results/eval_<account>_samples.csv` has one row per test recording, including what Prisma
heard. Check before committing it that the person agreed to transcripts of their speech
being published.

## Consent for a real person

Before you record anyone (`pilot`), get their informed consent in writing, in a language
they read comfortably, or recorded aloud if writing is hard for them. If they can't consent
for themselves, don't record them for this demo. Tell them, plainly:

- what Sunn is and that this is a student project for the Gnani Great Indian AI Internship
  Challenge, not a medical device or a clinical study
- what is recorded (the phrases), where it goes (sent to Gnani's speech service to be
  transcribed; stored on your computer and, if it's on the demo account, on the Hugging Face
  Space), and who can see what. Demo users can't play recordings back through the app, but
  they do see the phrases, and the evaluation's transcripts and accuracy may be published
  with the submission
- that it's voluntary, that they can stop at any time, and that they can ask you to delete
  everything later (delete the folder, the account with `DELETE /me`, and any published
  results that came from them)
- whether their voice will be cloned. Only with a separate, explicit yes, as the app asks

Collect no more than needed: no names in file names, no diagnosis details, no other personal
information. Keep the signed forms offline, never in the repo.

## TORGO

TORGO is a research database of dysarthric and control speech from the University of
Toronto (http://www.cs.toronto.edu/~complingweb/data/TORGO/torgo.html).
Read its licence or terms of use before you use it for anything public: putting its
recordings on the public demo Space, publishing results from it, or committing anything from
it. They haven't been checked for this project yet. If the terms don't clearly allow a use, don't do
it, or ask the maintainers. TORGO is English and was mostly read from prompts, so a TORGO demo
account uses `--language en`, and its results don't carry over to Hindi speakers.
