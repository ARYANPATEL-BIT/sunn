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

# recognize: top 3 bank phrases for a new Prisma hypothesis (lower distance = closer)
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
