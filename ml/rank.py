"""Shared by train_rerank.py, eval.py and export.py: the candidates, the rapidfuzz shortlist and
the cross-encoder's scores, so every script ranks the same way.

Inference: rapidfuzz scores every candidate (the backend's normalize, then Levenshtein; a
candidate scores as the closer of its Devanagari and Latin form), keeps the top SHORTLIST, and
the model reorders those.
"""
import os
import unicodedata

import numpy as np
import pandas as pd
import torch
from rapidfuzz import process
from rapidfuzz.distance import Levenshtein

from textnorm import SRC, normalize

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "train_all.csv")
MODEL_NAME = "google/muril-base-cased"
SHORTLIST = 10
MAX_LENGTH = 64
KIND = {"word": "words", "sentence": "sentences", "composed": "sentences"}  # source -> candidate pool
STARTER_BANK = os.path.join(os.path.dirname(SRC), "data", "default_phrases_hi.txt")


def nfc(text):
    return unicodedata.normalize("NFC", str(text))


def load_data():
    data = pd.read_csv(DATA, keep_default_na=False)
    data["heard"] = data.heard.astype(str)
    data["kind"] = data.source.map(KIND)
    return data


def candidates(rows):
    """The distinct intended texts in rows, indexed by their Devanagari text."""
    cands = rows.drop_duplicates("intended_hindi")[["intended_hindi", "intended_latin", "category"]]
    cands = cands.rename(columns={"intended_hindi": "hindi", "intended_latin": "latin"}).set_index("hindi", drop=False)
    cands["norm_hindi"] = cands.hindi.map(normalize)
    cands["norm_latin"] = cands.latin.map(normalize)
    return cands


def starter_bank():
    """The app's Hindi starter phrases (what every new user has), with their Latin from phrases.csv."""
    phrases = pd.read_csv(os.path.join(HERE, "phrases.csv"))
    latin = dict(zip(phrases.hindi.map(nfc), phrases.latin))
    with open(STARTER_BANK, encoding="utf-8") as f:
        texts = [nfc(" ".join(line.split())) for line in f if line.strip() and not line.startswith("#")]
    return candidates(pd.DataFrame({"intended_hindi": texts, "intended_latin": [latin.get(t, "") for t in texts],
                                    "category": "starter"}))


def candidate_text(hindi, latin):
    return f"{hindi} / {latin}" if latin else hindi


def fuzz_matrix(heard, cands):
    """0-100 similarity of each heard text (rows) to each candidate (columns)."""
    queries = [normalize(h) for h in heard]
    scores = [process.cdist(queries, list(cands[col]), scorer=Levenshtein.normalized_similarity, workers=-1)
              for col in ("norm_hindi", "norm_latin")]
    return 100 * np.maximum(*scores)


@torch.no_grad()
def model_scores(model, tokenizer, heard, texts, batch=512, bf16=True):
    """The cross-encoder's logit for each (heard, candidate text) pair. bf16 is for training only:
    the logits saturate near the classifier's bound, and bf16 rounds close ones into ties."""
    device = next(model.parameters()).device
    out = []
    for i in range(0, len(heard), batch):
        enc = tokenizer(heard[i:i + batch], texts[i:i + batch], padding=True, truncation=True,
                        max_length=MAX_LENGTH, return_tensors="pt").to(device)
        with torch.autocast(device.type, dtype=torch.bfloat16, enabled=bf16 and device.type == "cuda"):
            out.append(model(**enc).logits.float().view(-1).cpu())
    return torch.cat(out).numpy() if out else np.zeros(0)


def torch_scorer(model, tokenizer, bf16=False):
    return lambda heard, texts: model_scores(model, tokenizer, heard, texts, bf16=bf16)


def rank_of(scores, i):
    """1-based rank of scores[i]; a tie counts against it."""
    return 1 + int(np.sum(np.delete(scores, i) >= scores[i]))


def evaluate(heard, targets, cands, score_fn=None):
    """One dict per heard text: the intended text's rank under rapidfuzz (all candidates) and, with
    score_fn(heard, texts) -> logits, under the model (rapidfuzz's top SHORTLIST, reordered; None if
    rapidfuzz left it out), each one's top-1 and its top1-top2 margin (rapidfuzz in points of 100,
    the model in softmax probability over the shortlist)."""
    index = {h: i for i, h in enumerate(cands.hindi)}
    fuzz = fuzz_matrix(heard, cands)
    rows, short = [], []
    for f, target in zip(fuzz, targets):
        t = index[target]
        order = np.argsort(-f, kind="stable")[:SHORTLIST]
        top = np.sort(f)[::-1]
        rows.append({"fuzz_rank": rank_of(f, t), "fuzz_top1": cands.hindi.iloc[order[0]],
                     "fuzz_margin": float(top[0] - top[1]), "in_shortlist": t in order})
        short.append((order, t))
    if score_fn is None:
        return rows
    logits = score_fn([h for h, (order, _) in zip(heard, short) for _ in order],
                      [candidate_text(cands.hindi.iloc[i], cands.latin.iloc[i]) for order, _ in short for i in order])
    for k, (row, (order, t)) in enumerate(zip(rows, short)):
        s = logits[k * SHORTLIST:(k + 1) * SHORTLIST]
        p = np.exp(s - s.max())
        p = np.sort(p / p.sum())[::-1]
        row["model_top1"] = cands.hindi.iloc[order[int(np.argmax(s))]]
        row["model_margin"] = float(p[0] - p[1])
        row["model_rank"] = rank_of(s, list(order).index(t)) if t in order else None
    return rows


def top_k(rows, key, k):
    """Share of rows whose intended text ranks within the top k under key ("fuzz_rank" or "model_rank")."""
    return float(np.mean([r[key] is not None and r[key] <= k for r in rows])) if rows else float("nan")
