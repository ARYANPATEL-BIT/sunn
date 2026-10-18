import csv
import os

import matplotlib.pyplot as plt

from correct import load_predictions, split_repetitions
from matcher import normalize, recognize

OUT_CSV = "results/correction.csv"
OUT_PNG = "results/correction.png"


def evaluate_speaker(speaker):
    bank, held_out = split_repetitions(load_predictions(speaker))
    if not held_out:
        return None
    raw = top1 = top3 = 0
    for r in held_out:
        reference = normalize(r["reference"])
        top = [phrase for phrase, _ in recognize(r["hypothesis"], bank)]
        raw += normalize(r["hypothesis"]) == reference
        top1 += top[0] == reference
        top3 += reference in top
    n = len(held_out)
    return {
        "speaker": speaker,
        "is_dysarthric": speaker.startswith(("F0", "M0")),
        "n_phrases": len({e["phrase"] for e in bank}),
        "n_test": n,
        "raw_acc": round(raw / n, 3),
        "top1_acc": round(top1 / n, 3),
        "top3_acc": round(top3 / n, 3),
    }


def plot(results):
    # Categorical slots 1-3 of the dataviz reference palette; values are labelled
    # on the bars so identity never relies on colour alone.
    series = [("raw_acc", "Raw Prisma", "#2a78d6"),
              ("top1_acc", "Corrected top-1", "#eb6834"),
              ("top3_acc", "Corrected top-3", "#1baf7a")]
    width = 0.26
    fig, ax = plt.subplots(figsize=(max(7, 1.6 * len(results) + 2), 4))
    for i, (key, label, color) in enumerate(series):
        xs = [j + (i - 1) * width for j in range(len(results))]
        bars = ax.bar(xs, [r[key] for r in results], width - 0.03, label=label, color=color)
        ax.bar_label(bars, fmt="%.2f", fontsize=8, color="#52514e", padding=2)

    ax.set_xticks(range(len(results)), [f"{r['speaker']}\n(n={r['n_test']})" for r in results])
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Accuracy on held-out repetitions")
    ax.set_title("Personal correction layer vs raw Prisma", loc="left")
    ax.grid(axis="y", color="#e5e4e0")
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncols=3, loc="upper left", bbox_to_anchor=(0, -0.15))
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    speakers = sorted({r["speaker"] for r in load_predictions()})
    results = [r for r in (evaluate_speaker(s) for s in speakers) if r]

    os.makedirs("results", exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    for r in results:
        print(r)
    plot(results)
    print(f"saved {OUT_CSV} and {OUT_PNG}")
