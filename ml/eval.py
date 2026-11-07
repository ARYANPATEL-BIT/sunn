"""Compares rapidfuzz with the three rerankers on the same splits -> ml/results/compare.md.

Sets: test words (candidates: all 225 words), test sentences and composed test (candidates: all
310 phrases), and real_test.csv (candidates: the app's starter bank). Each model reorders
rapidfuzz's top 10. The margin threshold for handing a prediction to the LLM judge is picked on
val only, then reported on test. Nothing is tuned on test.
"""
import json
import os
from datetime import date

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

import rank

MODELS = {"words only": "ablation-words", "sentences only": "ablation-sentences", "both (rerank-v2)": "rerank-v2"}
REAL = os.path.join(rank.HERE, "data", "real_test.csv")
OUT = os.path.join(rank.HERE, "results", "compare.md")
PRECISION = 0.98  # a prediction is accepted without the LLM when its margin says it's right this often (on val)
SEVERITY = ["clean", "mild", "moderate", "severe"]


def pct(x):
    return "n/a" if x is None or np.isnan(x) else f"{100 * x:.1f}"


def threshold(margins, correct):
    """Smallest margin at which predictions with at least that margin are right PRECISION of the time."""
    margins, correct = np.asarray(margins), np.asarray(correct)
    for t in np.unique(margins):
        keep = margins >= t
        if correct[keep].mean() >= PRECISION:
            return float(t)
    return None


def routed(margins, correct, t):
    """(share sent to the LLM, top-1 of the rest) at threshold t."""
    margins, correct = np.asarray(margins), np.asarray(correct)
    if t is None:
        return 1.0, float("nan")
    keep = margins >= t
    return float(1 - keep.mean()), float(correct[keep].mean()) if keep.any() else float("nan")


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(lines + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def main():
    data = rank.load_data()
    words, sentences = rank.candidates(data[data.kind == "words"]), rank.candidates(data[data.kind == "sentences"])
    bank = rank.starter_bank()
    sets = {
        "test words": (data[(data.split == "test") & (data.source == "word")], words),
        "test sentences": (data[(data.split == "test") & (data.source == "sentence")], sentences),
        "composed test": (data[(data.split == "test") & (data.source == "composed")], sentences),
    }
    val = {"val words": (data[(data.split == "val") & (data.kind == "words")], words),
           "val sentences": (data[(data.split == "val") & (data.kind == "sentences")], sentences)}
    phrase_split = data[data.kind == "sentences"].drop_duplicates("intended_hindi").set_index("intended_hindi").split
    real = pd.read_csv(REAL, keep_default_na=False) if os.path.exists(REAL) else pd.DataFrame(columns=["file", "intended", "heard"])
    real["intended_hindi"] = real.intended.map(rank.nfc)
    real["severity"] = "unknown"
    real["trained_on"] = real.intended_hindi.map(lambda h: phrase_split.get(h) == "train")
    if len(real):
        sets["real test"] = (real, bank)

    available = {name: d for name, d in MODELS.items() if os.path.exists(os.path.join(rank.HERE, "models", d, "run.json"))}
    results = {}  # (set, system) -> rows
    for name, (rows, cands) in {**sets, **val}.items():
        out = rank.evaluate(list(rows.heard), list(rows.intended_hindi), cands)
        results[name, "rapidfuzz"] = out
    for system, folder in available.items():
        path = os.path.join(rank.HERE, "models", folder)
        tokenizer = AutoTokenizer.from_pretrained(path)
        model = AutoModelForSequenceClassification.from_pretrained(path).to("cuda" if torch.cuda.is_available() else "cpu").eval()
        for name, (rows, cands) in {**sets, **val}.items():
            results[name, system] = rank.evaluate(list(rows.heard), list(rows.intended_hindi), cands,
                                                  rank.torch_scorer(model, tokenizer))
        del model
        torch.cuda.empty_cache()
    systems = ["rapidfuzz", *available]
    key = lambda s: "fuzz" if s == "rapidfuzz" else "model"

    def scores(name, system, mask=None):
        rows = results[name, system]
        rows = rows if mask is None else [r for r, m in zip(rows, mask) if m]
        return rank.top_k(rows, f"{key(system)}_rank", 1), rank.top_k(rows, f"{key(system)}_rank", 3), len(rows)

    md = [f"# Correction model: comparison ({date.today()})", ""]
    md += ["## Real test: our recordings through Prisma (the only honest number)", ""]
    if "real test" in sets:
        n = len(real)
        md += [f"{n} recordings, candidates = the app's {len(bank)} starter phrases. Top-1 / top-3 in %.", ""]
        groups = {"all": None, "phrase never trained on": ~real.trained_on.to_numpy(), "phrase trained on": real.trained_on.to_numpy()}
        md += [table(["system", *[f"{g} top-1" for g in groups], "all top-3"],
                     [[s, *[f"{pct(scores('real test', s, m)[0])} (n={scores('real test', s, m)[2]})" for m in groups.values()],
                       pct(scores("real test", s)[1])] for s in systems]), ""]
        best = max(available, key=lambda s: scores("real test", s)[0], default=None)
        if best:
            gap = scores("real test", best)[0] - scores("real test", "rapidfuzz")[0]
            md += [f"Best reranker on real test: **{best}**, {100 * gap:+.1f} points over rapidfuzz "
                   f"({'it beats rapidfuzz' if gap > 0 else 'it does NOT beat rapidfuzz'}). With n={n}, one recording is "
                   f"{100 / n:.1f} points.", ""]
        md += ["| file | heard | intended | rapidfuzz | " + " | ".join(available) + " |", "|" + "---|" * (4 + len(available))]
        for i, r in enumerate(real.itertuples()):
            mark = lambda s: ("✓ " if results["real test", s][i][f"{key(s)}_top1"] == r.intended_hindi else "✗ ") + results["real test", s][i][f"{key(s)}_top1"]
            md.append(f"| {r.file} | {r.heard} | {r.intended_hindi} | {mark('rapidfuzz')} | " + " | ".join(mark(s) for s in available) + " |")
        md.append("")
    else:
        md += ["**Not run yet: no recordings.** Record them as in ml/RECORDING.md, then run "
               "`uv run run_real_test.py` and `uv run eval.py` again. Until then there is no evidence that the model "
               "helps on real Prisma output.", ""]

    md += ["## Synthetic test sets", "",
           "> **Synthetic numbers are not evidence.** The mistakes below were made by our own rules, so a model can learn "
           "the rules rather than Prisma's real mistakes. They show the code works and how the sources compare, nothing more.", ""]
    md += [table(["set", "n", "shortlist recall@10", *[f"{s} top-1" for s in systems], *[f"{s} top-3" for s in systems]],
                 [[name, len(sets[name][0]), pct(np.mean([r["in_shortlist"] for r in results[name, "rapidfuzz"]])),
                   *[pct(scores(name, s)[0]) for s in systems], *[pct(scores(name, s)[1]) for s in systems]]
                  for name in sets if name != "real test"]), ""]
    md += ["A model only reorders rapidfuzz's top 10, so shortlist recall@10 is the most any of them can reach. Models "
           "are scored in fp32: their logits saturate near the classifier's bound (about ±2.1, after BERT's tanh pooler), "
           "and bf16 rounds the top candidates into ties, which count as misses (rerank-v2 on test words: 75.8 in bf16, "
           "78.3 in fp32).", ""]

    md += ["### Top-1 per severity (%)", ""]
    for name in ("test words", "test sentences", "composed test"):
        rows = sets[name][0]
        present = [s for s in SEVERITY if (rows.severity == s).any()]
        md += [f"**{name}**", "", table(["system", *[f"{s} (n={int((rows.severity == s).sum())})" for s in present]],
                                         [[sy, *[pct(scores(name, sy, (rows.severity == s).to_numpy())[0]) for s in present]]
                                          for sy in systems]), ""]

    md += ["## When to ask the LLM judge: the top1-top2 margin", "",
           f"A threshold is the smallest margin at which accepted predictions are right at least {100 * PRECISION:.0f} % "
           "of the time on val; below it, the LLM judge decides. rapidfuzz margins are points out of 100, model margins "
           "softmax probability over the 10 candidates, which can't exceed about 0.88 because the logits are bounded. "
           "Cells are \"% sent to the LLM / top-1 of the rest\".", "",
           "**On val.** One threshold for words and sentences together doesn't hold for words: val alone shows it, so "
           "each kind gets its own threshold, also picked on val.", ""]
    margins = lambda name, s: ([r[f"{key(s)}_margin"] for r in results[name, s]], [r[f"{key(s)}_rank"] == 1 for r in results[name, s]])
    val_rows, test_rows, per_kind = [], [], {}
    for s in systems:
        pooled = [sum(x, []) for x in zip(*(margins(n, s) for n in val))]
        t = threshold(*pooled)
        per_kind[s] = {n: threshold(*margins(n, s)) for n in val}
        fmt = lambda t: "none reaches it" if t is None else f"{t:.3f}"
        val_rows.append([s, fmt(t), *[f"{pct(routed(*margins(n, s), t)[0])} / {pct(routed(*margins(n, s), t)[1])}" for n in val],
                         *[f"{fmt(per_kind[s][n])}: {pct(routed(*margins(n, s), per_kind[s][n])[0])} / "
                           f"{pct(routed(*margins(n, s), per_kind[s][n])[1])}" for n in val]])
        line = [s]
        for name in sets:
            t = per_kind[s]["val words" if name == "test words" else "val sentences"]
            share, acc = routed(*margins(name, s), t)
            q = np.percentile(margins(name, s)[0], [10, 50, 90])
            line.append(f"{pct(share)} / {pct(acc)} (p10 {q[0]:.2f}, p50 {q[1]:.2f}, p90 {q[2]:.2f})")
        test_rows.append(line)
    md += [table(["system", "one threshold", *[f"{n} at it" for n in val], *[f"{n}: own threshold, then at it" for n in val]],
                 val_rows), ""]
    md += ["**On test**, with the per-kind thresholds from val, unchanged (words for test words, sentences for the rest):", "",
           table(["system", *[f"{n} (margin p10 / p50 / p90)" for n in sets]], test_rows), ""]

    md += ["## Ablation: does combining the sources help?", ""]
    abl = []
    for s, folder in available.items():
        with open(os.path.join(rank.HERE, "models", folder, "run.json"), encoding="utf-8") as f:
            info = json.load(f)
        abl.append([s, info["best_epoch"], info.get("epochs_run", "?"), info.get("train_minutes", "?"),
                    pct(info["val_top1"]["words"]), pct(info["val_top1"]["sentences"]), pct(info["val_score"]),
                    *[pct(scores(n, s)[0]) for n in sets]])
    base = [rank.top_k(results[n, "rapidfuzz"], "fuzz_rank", 1) for n in val]
    abl.append(["rapidfuzz", "-", "-", "-", *[pct(b) for b in base], pct(np.mean(base)),
                *[pct(scores(n, "rapidfuzz")[0]) for n in sets]])
    md += [table(["system", "best epoch", "epochs run", "train min", "val top-1 words", "val top-1 sentences", "val score",
                  *[f"{n} top-1" for n in sets]], abl), ""]
    md += ["Every run uses the same train/val/test split (ml/data/train_all.csv) and picks its best epoch by the same val "
           "score (mean of val top-1 on words and on sentences), with patience 2. One run per setup (seed 7): GPU training "
           "isn't bit-reproducible, and two runs of rerank-v2 with the same seed differed by up to 18 points of val words "
           "top-1 at the same epoch (epoch 2: 59.1 vs 77.1), so gaps of a few points between runs are noise.", ""]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
