"""Downloads the Vaani atypical speech corpus to ml/data/vaani: one wav per clip, plus metadata.csv.

Research use only: never put this audio in the backend, the Docker image or the Space.
Uses the Hugging Face login from `hf auth login`.
"""
import csv
import os

from datasets import Audio, Value, load_dataset

REPO = "ARTPARK-IISc/Vaani-Atypical-Speech-Corpus"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "vaani")
WAV = os.path.join(OUT, "wav")

os.makedirs(WAV, exist_ok=True)
dataset = load_dataset(REPO, cache_dir=os.path.join(HERE, "data", "hf_cache"))
rows, skipped = [], 0
for split, ds in dataset.items():
    audio_col = next(name for name, f in ds.features.items() if isinstance(f, Audio))
    # Only plain values and the audio, so image or video columns are never decoded.
    text_cols = [name for name, f in ds.features.items() if isinstance(f, Value)]
    ds = ds.select_columns([audio_col, *text_cols]).cast_column(audio_col, Audio(decode=False))
    for i, row in enumerate(ds):
        data = row[audio_col] and row[audio_col].get("bytes")
        if not data:
            skipped += 1
            continue
        name = f"{split}_{i}.wav"
        with open(os.path.join(WAV, name), "wb") as f:
            f.write(data)
        rows.append({"file": name, "split": split, **{c: row[c] for c in text_cols}})

with open(os.path.join(OUT, "metadata.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"wrote {len(rows)} clips to {WAV}, skipped {skipped} without audio bytes")
