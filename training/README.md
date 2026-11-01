# Shared model experiment

A research question, kept apart from the app: can whisper-small, fine-tuned with LoRA on
atypical speech, transcribe speakers it has never heard? And if it can, does it help Sunn pick
the right phrase? Sunn itself doesn't change. Prisma and Timbre stay its core, and its
recognition stays per person (README.md, "How it works").

The app gets a shared model only if the evaluation's gate passes (below). Until then this is
an experiment, and nothing here runs in the app or ships in the Docker image.

**Status: not run on real data yet.** The scripts have been run end to end on a few made-up
clips (tones, to check the code on the RTX 5070), so there are no results to report.

## The data, and consent

Two kinds of input:

- **Export folders**: any folder of recordings with a `metadata.csv`, UTF-8, one row per clip:

  ```csv
  file,text,language,speaker_id,source
  water-1.wav,पानी चाहिए,hi,p01,pilot
  help-1.wav,I need help,en,p02,pilot
  ```

  `file` is relative to the folder (anything ffmpeg reads), `text` is what was said, `language`
  is `hi` or `en`, `speaker_id` is one ID per person (no names), `source` is where the speech
  came from (`pilot`, `torgo`, `simulated`, as in docs/DEMO_DATA.md).
- **TORGO** (`--torgo data/torgo`), the corpus as distributed:
  `data/torgo/<speaker>/Session*/wav_arrayMic/0001.wav` with the prompt in `prompts/0001.txt`.
  Only the dysarthric speakers are used (control speakers have a `C` in their ID), one
  microphone per session (the array microphone, else the head-worn one). Prompts that ask the
  speaker to describe a picture, or that have no text, are skipped. Check TORGO's licence before
  publishing anything trained or measured on it (docs/DEMO_DATA.md).

There is deliberately **no script that exports recordings from Sunn accounts**. Sunn's sign-up
consent covers recording someone "so it can learn how you speak": their own phrases, for
their own recognition. Training a model that other people use is a different purpose, and
README.md promises that one person's patterns are never averaged with anyone else's.
Before any app user's recordings go into an export folder, the app would need a separate,
explicit "donate my recordings to train a shared model" consent that can be withdrawn, and
README.md's privacy section would need updating. Until then, export folders hold recordings
from people who agreed to this use directly, recorded as in docs/DEMO_DATA.md.

Keep export folders under `data/` (ignored by git), and never commit recordings.

## Setup

PyTorch with CUDA 12.8 (needed for Blackwell GPUs such as the RTX 50 series) and the training
libraries are in their own dependency group, so neither the app nor the image installs them:

```powershell
uv sync --group train
uv run --group train python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

A plain `uv sync` removes the group again; `uv run` leaves it installed.

## 1. Split by speaker

```powershell
uv run --group train training/data.py --exports data/export-1 data/export-2 --torgo data/torgo
```

Prints speakers, clips and minutes for each split and language, and a loud warning when a split
has fewer than 3 speakers or 10 minutes. The first run picks the held-out (test) speakers, 20 %
of each language's speakers and at least 1 when the language has 2 or more, with a fixed seed,
and saves them to `training/splits.json`. Every later run reuses that file, so the test speakers
never change and never end up in training. Speakers added later are left out with a warning;
delete `training/splits.json` to split again (this changes who is held out, so earlier results
no longer compare).

Clips of `source` `simulated` are left out unless `--include-simulated` is passed: imitated
unclear speech isn't atypical speech. Clips over 15 s or without text are dropped too.

## 2. Train

```powershell
uv run --group train training/train.py --exports data/export-1 --torgo data/torgo --run-name first
```

whisper-small with LoRA (r 16, alpha 32, dropout 0.05) on the q and v projections of every
attention layer, everything else frozen; 1.8 M trainable parameters of 244 M. Each clip is
decoded with its own language token. bf16, gradient checkpointing, batches of 8 accumulated to
32, learning rate 1e-4 with warmup, 4000 steps (`--steps`). Training clips get a random speed
(0.9, 1.0 or 1.1) and white noise at 15-30 dB SNR.

5 % of the train speakers' clips (at most 200) are kept back for validation. Every 250 steps
their CER is measured, and the adapter is saved whenever it is the best so far. These are
speakers the model trains on, so the validation CER is optimistic: only the held-out speakers'
numbers (step 3) count.

Output: `models/shared/<run>/` (the LoRA adapter, and `run.json` with the settings, the split and
the git commit) and `training/runs/<run>.csv` (step, loss, learning rate, batch, validation CER).
Both are ignored by git: an adapter is learned from people's speech.

On the RTX 5070 laptop GPU (8 GB) a step took about 6 s in the smoke run, so 4000 steps take
about 7 hours. Batch 8 used about 4 GB. If the GPU runs out of memory, the batch halves and the
accumulation doubles, keeping 32 a step. PyTorch is capped at 90 % of the GPU's memory, because
Windows drivers otherwise spill into system RAM and slow down instead of failing. Data loading
uses 2 worker processes (`--workers`) and falls back to 0 if they fail.

## 3. Evaluate, on the held-out speakers only

Run it from the repository root, so it finds Prisma's cache in `data/cache/prisma`, with
`GNANI_API_KEY` in `.env` and `GNANI_MOCK` off:

```powershell
uv run --group train training/evaluate.py --run-name first --exports data/export-1 --torgo data/torgo
```

It compares, on the same clips:

- zero-shot whisper-small, the fine-tuned adapter, and Prisma's raw transcript. Prisma
  transcripts are read from the cache. At most 200 uncached clips are sent
  (`--max-gnani-calls`), and the output says how many were.
- CER for Hindi (in Devanagari: a romanized transcript counts as wrong), and WER and CER for
  English. Before scoring, text is lower-cased and punctuation is removed.
- phrase top-1: each transcript matched to the closest of the speaker's phrases, with
  `matcher.similarity`. `sunn` is today's pipeline: Prisma's transcript ranked by `matcher.rank`
  against the speaker's other recordings of each phrase (leave one out). `sunn + fine-tuned` adds
  the model's similarity to each phrase's text, with a weight fixed at 1 before seeing any
  results. Ties count as misses, and so do empty transcripts.

It writes `results/shared_model_eval.csv` (every number, with n),
`results/shared_model_eval_samples.csv` (every clip with every transcript: check the speakers
agreed to publication before committing it) and `results/shared_model_eval.png`.

### The gate

It prints its decision and the reasons. It passes only if both are true:

1. The fine-tuned model beats zero-shot whisper on every held-out language (Hindi CER, English
   WER).
2. `sunn + fine-tuned` beats `sunn`'s phrase top-1 by at least 5 percentage points.

If it doesn't pass, the shared model stays research. Record the real numbers in README.md under
"Shared model experiment", along with what more data would be needed. If it passes, the next
step (not built) is to merge the adapter, export it with CTranslate2 (int8) for CPU inference,
add it to recognition as a `model` score part behind a `SHARED_MODEL` flag, tune its weight on
validation speakers, and measure CPU latency. That is an API change, and it needs the donation
consent described above.

## Honest limits

- **Few speakers.** A model that generalizes across atypical speech needs many speakers. With a
  handful, the held-out set is one or two people, and results on it are anecdotes, not
  evidence. Every split is printed with its speaker count for this reason.
- **TORGO is English only**, mostly read prompts, recorded in a lab. It can't show anything
  about Hindi, and transfer to spontaneous phrases at home is unknown.
- **There is no public Hindi atypical-speech dataset** that this project knows of. Hindi results
  depend entirely on recordings people choose to donate.
- Phrase top-1 matches against all the phrases a speaker has in the data. For a TORGO speaker
  that is hundreds of prompts, much harder than a Sunn account's ~50 phrases. The `sunn`
  baseline has no context or usage boosts.
- The noise augmentation is white noise, not recorded background noise.
- The fusion weight is fixed at 1, not tuned. A tuned weight might do better, but this one can't
  have been fitted to the test speakers.
