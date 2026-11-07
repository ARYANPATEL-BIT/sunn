"""Builds ml/data/train_all.csv: the word variants (A) and the sentence variants (B) in one schema,
plus sentences composed from word variants.

A  ml/data/sunn_word_variants.csv (ml/make-word-varients.py): one Hindi word per row, split by word.
B  ml/data/synthetic.csv (ml/make_synthetic.py, phrases in ml/phrases.csv): split by phrase.
composed: for every phrase (B and the app's starter banks) whose words are all in A, 5 versions
   made by replacing each word with a random heard variant of it from A (बानी चाइए -> पानी चाहिए).

One split rule for every sentence: a phrase with any A test word is test; else with any A val
word, val; else it keeps B's split. Composed rows take their phrase's split (a composed "दूध चाहिए"
in train next to B's "दूध चाहिए" in test would leak the phrase). Nothing ever moves into train.
"""
import os
import random
import unicodedata
from collections import Counter

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
STARTER = os.path.join(os.path.dirname(HERE), "data", "default_phrases_{}.txt")
OUT = os.path.join(DATA, "train_all.csv")
COLUMNS = ["heard", "intended_hindi", "intended_latin", "meaning_en", "category", "severity", "source", "split"]
COMPOSED_PER_PHRASE = 5
SEED = 11
HELD_OUT = {"test": 0, "val": 1, "train": 2}  # lower = more held out
SEVERITY = ["clean", "mild", "moderate", "severe"]


def nfc(text):
    return unicodedata.normalize("NFC", str(text))


def words_of(text):
    return [nfc(w.strip(",.?!")) for w in text.split()]


def main():
    words = pd.read_csv(os.path.join(DATA, "sunn_word_variants.csv"), encoding="utf-8-sig", keep_default_na=False)
    sentences = pd.read_csv(os.path.join(DATA, "synthetic.csv"), keep_default_na=False)
    phrases = pd.read_csv(os.path.join(HERE, "phrases.csv"))
    for df, cols in ((words, ["heard", "intended_hindi"]), (sentences, ["heard", "intended"]), (phrases, ["hindi"])):
        for col in cols:
            df[col] = df[col].map(nfc)

    word_split = dict(zip(words.intended_hindi, words.split))
    variants = {w: list(zip(g.heard, g.severity)) for w, g in words.groupby("intended_hindi")}

    def split_by_words(text, own):
        found = {word_split[w] for w in words_of(text) if w in word_split}
        for held, reason in (("test", "an A test word"), ("val", "an A val word")):
            if held in found and HELD_OUT[held] < HELD_OUT[own]:
                bad = [w for w in words_of(text) if word_split.get(w) == held]
                return held, f"{own} -> {held} ({reason}: {', '.join(bad)})"
        return own, None

    # --- word rows, as they are ---
    word_rows = words.assign(source="word")[COLUMNS]

    # --- sentence rows: B, with the shared split rule ---
    phrase_split, moves = {}, []
    b_split = sentences.drop_duplicates("phrase_id").set_index("phrase_id").split
    for p in phrases.itertuples():
        phrase_split[p.hindi], why = split_by_words(p.hindi, b_split[p.phrase_id])
        if why:
            moves.append((p.hindi, why))
    sentence_rows = pd.DataFrame({
        "heard": sentences.heard, "intended_hindi": sentences.intended, "intended_latin": sentences.intended_latin,
        "meaning_en": sentences.meaning_en, "category": sentences.place, "severity": sentences.severity,
        "source": "sentence", "split": sentences.intended.map(phrase_split)})

    # --- composed rows: every phrase whose words are all in A ---
    targets = {p.hindi: (p.latin, p.meaning_en, p.place) for p in phrases.itertuples()}
    for lang in ("hi", "en"):
        with open(STARTER.format(lang), encoding="utf-8") as f:
            for line in f:
                text = nfc(" ".join(line.split()))
                if text and not line.startswith("#") and text not in targets:
                    targets[text] = ("", text if lang == "en" else "", "any")
    rng = random.Random(SEED)
    composed = []
    for text, (latin, meaning, place) in targets.items():
        parts = words_of(text)
        if not all(w in variants for w in parts):
            continue
        split = phrase_split.get(text) or split_by_words(text, "train")[0]
        made = set()
        for _ in range(50):
            if len(made) == COMPOSED_PER_PHRASE:
                break
            picks = [rng.choice(variants[w]) for w in parts]
            heard = " ".join(h for h, _ in picks)
            if heard == text or heard in made:
                continue
            made.add(heard)
            worst = max((s for _, s in picks), key=SEVERITY.index)
            composed.append({"heard": heard, "intended_hindi": text, "intended_latin": latin, "meaning_en": meaning,
                             "category": place, "severity": worst, "source": "composed", "split": split})
    composed_rows = pd.DataFrame(composed, columns=COLUMNS)

    # --- duplicates: keep the most held-out copy, so a test example is never also in train ---
    data = pd.concat([word_rows, sentence_rows, composed_rows], ignore_index=True)
    data["_held"] = data.split.map(HELD_OUT)
    data = data.sort_values("_held", kind="stable")
    dup = data.duplicated(["heard", "intended_hindi"])
    dropped = data[dup]
    data = data[~dup].drop(columns="_held").sort_index().reset_index(drop=True)
    data.to_csv(OUT, index=False, encoding="utf-8")

    print(f"wrote {len(data)} rows to {OUT}\n")
    print(f"phrases moved by the shared split rule: {len(moves)} (sentence rows moved: "
          f"{int(sentences.intended.isin([m[0] for m in moves]).sum())})")
    for kind, n in Counter(why.split(" (")[0] for _, why in moves).most_common():
        print(f"  {kind}: {n} phrases")
    blame = Counter(w for _, why in moves for w in why.split(": ")[1].rstrip(")").split(", "))
    print("  words that caused it:", ", ".join(f"{w} {n}" for w, n in blame.most_common()))
    print(f"\ncomposed: {composed_rows.intended_hindi.nunique()} phrases have every word in A,"
          f" {len(composed_rows)} rows: {', '.join(composed_rows.intended_hindi.unique())}")
    print(f"\nexact duplicates dropped (same heard + intended): {len(dropped)}",
          dict(Counter(zip(dropped.source, dropped.split))))
    ambiguous = data.groupby("heard").intended_hindi.nunique()
    ambiguous = ambiguous[ambiguous > 1]
    print(f"heard texts that map to more than one intended phrase (kept, real ambiguity): {len(ambiguous)}")
    for heard in ambiguous.index[:8]:
        print(f"  {heard!r} -> {sorted(data[data.heard == heard].intended_hindi.unique())}")
    train_targets = set(data[data.split == "train"].intended_hindi)
    overlap = sorted(set(data[data.split != "train"].intended_hindi) & train_targets)
    print(f"val/test intended texts that are also a train intended text (across sources): {overlap or 'none'}")

    print("\nrows per source x split:")
    print(pd.crosstab(data.source, data.split, margins=True, margins_name="total")[["train", "val", "test", "total"]].to_string())
    print("\nintended texts per source x split:")
    print(data.groupby(["source", "split"]).intended_hindi.nunique().unstack()[["train", "val", "test"]].to_string())
    print("\nrows per severity x source:")
    print(pd.crosstab(data.severity, data.source, margins=True, margins_name="total").reindex(SEVERITY + ["total"]).to_string())


if __name__ == "__main__":
    main()
