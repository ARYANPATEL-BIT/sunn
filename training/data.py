"""Clips for the shared-model experiment, and a fixed split of them by speaker.

Sources:
    export folders  wav files + metadata.csv with the columns file, text, language (hi or en),
                    speaker_id and source (pilot, torgo, simulated...). Only recordings whose
                    speakers agreed to their speech training a shared model belong here: Sunn's
                    sign-up consent covers learning that one person's speech, not this.
    TORGO           the corpus as distributed (data/torgo/<speaker>/Session*/wav_arrayMic/0001.wav
                    with the prompt in prompts/0001.txt). Dysarthric speakers only (control
                    speakers have a C in their id), English, one microphone per session.

Every clip is a dict: path, text, language, speaker, source, seconds. Audio is read at 16 kHz mono.
Simulated speech is left out unless asked for: it isn't atypical speech.

    uv run --group train training/data.py --exports data/export-1 --torgo data/torgo
"""
import argparse
import csv
import json
import os
import random
import re
import sys
from collections import defaultdict

import librosa
import numpy as np
import soundfile

RATE = 16000
MAX_SECONDS = 15
SPLITS = os.path.join("training", "splits.json")
SEED = 1234
TEST_SHARE = 0.2  # of each language's speakers, at least 1 when the language has 2 or more
MIN_SPEAKERS, MIN_MINUTES = 3, 10  # below either, a split is too small to say much
COLUMNS = ["file", "text", "language", "speaker_id", "source"]


def from_export(folder):
    with open(os.path.join(folder, "metadata.csv"), encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = set(COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"{folder}/metadata.csv lacks the columns {', '.join(sorted(missing))}")
        return [{"path": os.path.join(folder, r["file"].strip()), "text": " ".join(r["text"].split()),
                 "language": r["language"].strip(), "speaker": r["speaker_id"].strip(),
                 "source": r["source"].strip()} for r in reader]


def from_torgo(root):
    """TORGO prompts that are a picture to describe (a .jpg path) or say nothing ("xxx") are
    skipped: there is no reference text to train on."""
    clips = []
    for speaker in sorted(os.listdir(root)):
        if "C" in speaker or not os.path.isdir(os.path.join(root, speaker)):
            continue
        for session in sorted(os.listdir(os.path.join(root, speaker))):
            base = os.path.join(root, speaker, session)
            mic = next((m for m in ("wav_arrayMic", "wav_headMic") if os.path.isdir(os.path.join(base, m))), None)
            if mic is None or not os.path.isdir(os.path.join(base, "prompts")):
                continue
            for name in sorted(os.listdir(os.path.join(base, mic))):
                prompt = os.path.join(base, "prompts", name.replace(".wav", ".txt"))
                if not name.endswith(".wav") or not os.path.isfile(prompt):
                    continue
                with open(prompt, encoding="utf-8", errors="replace") as f:
                    text = " ".join(f.read().split())
                if ".jpg" in text or "xxx" in text.lower():
                    continue
                clips.append({"path": os.path.join(base, mic, name), "text": re.sub(r"\[.*?\]", "", text).strip(),
                              "language": "en", "speaker": f"torgo-{speaker}", "source": "torgo"})
    return clips


def load_audio(path):
    """float32 at 16 kHz, mono."""
    samples, _ = librosa.load(path, sr=RATE, mono=True)
    return samples


def collect(exports=(), torgo=None, include_simulated=False):
    """Every usable clip, with its length. Drops simulated speech (unless asked), empty text,
    unreadable files and clips over MAX_SECONDS, and says how many."""
    clips = [c for folder in exports for c in from_export(folder)] + (from_torgo(torgo) if torgo else [])
    kept, dropped = [], defaultdict(int)
    for clip in clips:
        if clip["source"] == "simulated" and not include_simulated:
            dropped["simulated"] += 1
        elif not clip["text"]:
            dropped["empty text"] += 1
        elif clip["language"] not in ("hi", "en"):
            dropped[f"language {clip['language']!r}"] += 1
        else:
            try:
                clip["seconds"] = soundfile.info(clip["path"]).duration
            except RuntimeError:
                dropped["unreadable"] += 1
                continue
            if clip["seconds"] > MAX_SECONDS:
                dropped[f"over {MAX_SECONDS} s"] += 1
            else:
                kept.append(clip)
    for reason, n in sorted(dropped.items()):
        print(f"dropped {n} clips: {reason}")
    return kept


def split(clips, path=SPLITS, seed=SEED):
    """{"train": [speakers], "test": [speakers]}, read from path when it exists so every run
    holds out the same people; else made (seeded, per language) and saved there. A speaker
    never ends up in both. A language with one speaker has nobody to hold out."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            splits = json.load(f)
        new = sorted({c["speaker"] for c in clips} - set(splits["train"]) - set(splits["test"]))
        if new:
            print(f"WARNING: {len(new)} speakers aren't in {path} and are left out: {', '.join(new)}. "
                  f"Delete {path} to split again (the held-out speakers will change).")
        return splits

    rng = random.Random(seed)
    splits = {"seed": seed, "train": [], "test": []}
    by_language = defaultdict(set)
    for clip in clips:
        by_language[clip["language"]].add(clip["speaker"])
    for language, speakers in sorted(by_language.items()):
        speakers = sorted(speakers)
        rng.shuffle(speakers)
        n_test = max(1, round(TEST_SHARE * len(speakers))) if len(speakers) > 1 else 0
        if not n_test:
            print(f"WARNING: only 1 {language} speaker, so no {language} speaker is held out")
        held = [s for s in speakers[:n_test] if s not in splits["train"]]
        splits["test"] += held
        splits["train"] += [s for s in speakers if s not in held and s not in splits["test"]]
    splits["train"], splits["test"] = sorted(set(splits["train"])), sorted(set(splits["test"]))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(splits, f, indent=2, ensure_ascii=False)
    print(f"saved a new speaker split to {path}")
    return splits


def report(clips, splits):
    """Print speakers, clips and minutes per split and language; shout about thin splits."""
    for name in ("train", "test"):
        part = [c for c in clips if c["speaker"] in splits[name]]
        for language in sorted({c["language"] for c in clips}):
            group = [c for c in part if c["language"] == language]
            speakers, minutes = len({c["speaker"] for c in group}), sum(c["seconds"] for c in group) / 60
            sources = ", ".join(sorted({c["source"] for c in group})) or "-"
            print(f"{name:>5} {language}: {speakers} speakers, {len(group)} clips, {minutes:.1f} min ({sources})")
            if speakers < MIN_SPEAKERS or minutes < MIN_MINUTES:
                print(f"  !!! WARNING: {name} {language} has {speakers} speakers and {minutes:.1f} minutes "
                      f"(fewer than {MIN_SPEAKERS} speakers or {MIN_MINUTES} minutes). Results on it are anecdotes.")


def speed(samples, factor):
    """Speed perturbation (tempo and pitch together, as in Kaldi): factor 1.1 is 10 % faster."""
    return samples if factor == 1.0 else librosa.resample(samples, orig_sr=RATE * factor, target_sr=RATE)


def noise(samples, snr_db, rng):
    """White noise at snr_db below the clip's power."""
    power = np.mean(samples ** 2) or 1e-10
    return samples + rng.normal(0, np.sqrt(power / 10 ** (snr_db / 10)), len(samples)).astype(np.float32)


def augment(samples, rng):
    """For training clips only: a random speed of 0.9, 1.0 or 1.1 and noise at 15-30 dB SNR."""
    return noise(speed(samples, rng.choice([0.9, 1.0, 1.1])), rng.uniform(15, 30), rng)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exports", nargs="*", default=[], help="folders with metadata.csv")
    parser.add_argument("--torgo", help="the TORGO folder, e.g. data/torgo")
    parser.add_argument("--include-simulated", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    found = collect(args.exports, args.torgo, args.include_simulated)
    if not found:
        raise SystemExit("no usable clips")
    report(found, split(found))
