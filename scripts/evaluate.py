"""Evaluate Sunn on an account's held-out recordings: the test rows of a demo folder's manifest.

Each test recording is converted as the API converts uploads and sent to Prisma (cached in
DATA_DIR, so a second run sends nothing; a new one counts against GNANI_CALL_LIMIT but not a
daily cap). Its hypothesis is then ranked the way POST /me/recognize ranks it (matcher.rank),
against the account's phrases and their enrollment recordings in the account's language.
Confirmed recognitions, template compositions and usage boosts are left out: a demo account
has no usage history, and the test is how far the enrollment recordings alone get.

Reported, overall and per source (pilot, torgo, simulated):
    raw_exact       Prisma's hypothesis is the phrase, after matcher.normalize (case, punctuation, script)
    top1, top3      the phrase is Sunn's first candidate, or among its three
    *_context       the same with the context set to the phrase's own first context (home,
                    hospital or market): the best case, where the user picked the right place.
                    A phrase tagged only "any" gets no context, so for it on and off are the same
    *_k1, _k2, _k3  each phrase matched on only its first 1, 2 or 3 enrollment recordings
                    (fewer when it has fewer), context off

Reads the account from DATA_DIR (default data/), so load the demo into a local server first
(scripts/load_demo.py). Writes results/eval_<account>.csv (the summary),
results/eval_<account>_samples.csv (one row per test recording, with what Prisma heard) and
three charts, results/eval_<account>_*.png.

    uv run scripts/evaluate.py --email demo@example.com --folder data/demo
"""
import argparse
import csv
import os
import re
import sys
import tempfile
from collections import Counter

import matplotlib

matplotlib.use("Agg")  # files only, no window
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import audio  # noqa: E402
import db  # noqa: E402
import gnani_mock  # noqa: E402
import matcher  # noqa: E402
import prisma  # noqa: E402
from load_demo import SOURCES, read_manifest  # noqa: E402

RESULTS = "results"
KS = (1, 2, 3)
# Reference palette slots 1-3 (the dataviz skill), validated as a set; labels carry the values.
COLORS = ("#2a78d6", "#eb6834", "#1baf7a")
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e5e4e0", "#fcfcfb"


def bank(user):
    """{phrase text: (contexts, [enrollment hypotheses, oldest first])} for each phrase with at
    least one enrollment recording in the user's current language."""
    found = {}
    for s in db.rows("SELECT p.text, p.contexts, s.prisma_hypothesis FROM samples s JOIN phrases p ON p.id = s.phrase_id"
                     " WHERE s.user_id = ? AND s.source = 'enroll' AND s.language = ? ORDER BY s.id",
                     (user["id"], user["language"])):
        found.setdefault(s["text"], (s["contexts"].split(","), []))[1].append(s["prisma_hypothesis"])
    return found


def hear(path, language):
    """What Prisma hears in a recording, converted exactly as an upload is (audio.to_wav)."""
    with tempfile.TemporaryDirectory() as folder:
        wav = os.path.join(folder, "test.wav")
        audio.to_wav(path, wav)
        return prisma.transcribe(wav, language)


def ranked(hypothesis, phrases, k=None, context=None):
    """Phrase texts, best first (at most 3), as recognize would rank them; none for no speech."""
    if not hypothesis.strip():
        return []
    candidates = [{"key": text, "fingerprints": hypotheses[:k], "contexts": contexts}
                  for text, (contexts, hypotheses) in phrases.items()]
    return [c["key"] for c in matcher.rank(hypothesis, candidates, context)]


def score(row, hypothesis, phrases):
    """One test recording's results: each metric is 1 when Sunn (or Prisma) got it right."""
    text = row["phrase"]
    context = next((c for c in phrases[text][0] if c in ("home", "hospital", "market")), None)
    result = {"file": row["file"], "source": row["source"], "phrase": text, "hypothesis": hypothesis,
              "context": context or "", "raw_exact": int(matcher.normalize(hypothesis) == matcher.normalize(text))}
    for suffix, k, ctx in [("", None, None), ("_context", None, context)] + [(f"_k{k}", k, None) for k in KS]:
        top = ranked(hypothesis, phrases, k, ctx)
        result[f"top1{suffix}"], result[f"top3{suffix}"] = int(top[:1] == [text]), int(text in top)
    return result


METRICS = ["raw_exact", "top1", "top3", "top1_context", "top3_context"] + [f"top{n}_k{k}" for k in KS for n in (1, 3)]


def summarize(samples, phrases):
    """Rows of the summary: every metric over all test recordings, then over each source's."""
    groups = [("all", samples)] + [(s, [r for r in samples if r["source"] == s]) for s in SOURCES]
    rows = []
    for source, group in groups:
        for metric in METRICS if group else []:
            correct = sum(r[metric] for r in group)
            rows.append({"source": source, "metric": metric, "correct": correct, "n": len(group),
                         "accuracy": f"{correct / len(group):.3f}", "bank_phrases": len(phrases),
                         "test_phrases": len({r["phrase"] for r in group})})
    return rows


def describe(samples, phrases):
    """The data a chart is about, for its title: what it is, and how much of it."""
    sources = Counter(r["source"] for r in samples)
    mix = ", ".join(f"{source} {n}" for source, n in sorted(sources.items()))
    return (f"{len(samples)} held-out recordings ({mix}), {len({r['phrase'] for r in samples})} phrases, "
            f"{len(phrases)} enrolled phrases to choose from")


def bars(ax, groups, series, value):
    """Grouped bars: groups is [label], series is [(label, [rows])]; each bar says correct/n."""
    width = min(0.8 / len(series), 0.22)
    for i, ((label, rows), color) in enumerate(zip(series, COLORS)):
        xs = [j + (i - (len(series) - 1) / 2) * width for j in range(len(groups))]
        heights = [value(r) for r in rows]
        drawn = ax.bar(xs, heights, width - 0.04, label=label, color=color)
        ax.bar_label(drawn, [f"{r['correct']}/{r['n']}" for r in rows], fontsize=8, color=MUTED, padding=2)
    ax.set_xticks(range(len(groups)), groups)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Share of held-out recordings")
    ax.grid(axis="y", color=GRID)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncols=len(series), loc="upper left", bbox_to_anchor=(0, -0.12))


def chart(name, title, subtitle, draw):
    fig, ax = plt.subplots(figsize=(8, 4.4), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    draw(ax)
    ax.set_title(f"{title}\n{subtitle}", loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    path = os.path.join(RESULTS, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot(account, summary, samples, phrases):
    subtitle = describe(samples, phrases)
    find = {(r["source"], r["metric"]): r for r in summary}
    sources = [s for s in SOURCES if (s, "top1") in find]
    groups = sources + (["all"] if len(sources) > 1 else [])
    paths = [chart(
        f"eval_{account}_accuracy.png", "Raw Prisma vs Sunn, by where the speech came from", subtitle,
        lambda ax: bars(ax, [f"{g}\n(n={find[g, 'top1']['n']})" for g in groups],
                        [(label, [find[g, metric] for g in groups]) for metric, label in
                         [("raw_exact", "Raw Prisma, exact match"), ("top1", "Sunn top-1"), ("top3", "Sunn top-3")]],
                        lambda r: r["correct"] / r["n"]))]
    paths.append(chart(
        f"eval_{account}_context.png", "Context off vs on (on = the phrase's own context, the best case)", subtitle,
        lambda ax: bars(ax, ["top-1", "top-3"],
                        [("Context off", [find["all", "top1"], find["all", "top3"]]),
                         ("Context on", [find["all", "top1_context"], find["all", "top3_context"]])],
                        lambda r: r["correct"] / r["n"])))
    most = max(len(hypotheses) for _, hypotheses in phrases.values())
    ks = [k for k in KS if k <= most]
    have = {k: sum(len(hypotheses) >= k for _, hypotheses in phrases.values()) for k in ks}
    paths.append(chart(
        f"eval_{account}_enrollments.png", "Accuracy vs enrollment recordings per phrase (context off)", subtitle,
        lambda ax: bars(ax, [f"{k} recording{'s' * (k > 1)}\n({have[k]} of {len(phrases)} phrases have {k})" for k in ks],
                        [(f"Sunn top-{n}", [find["all", f"top{n}_k{k}"] for k in ks]) for n in (1, 3)],
                        lambda r: r["correct"] / r["n"])))
    return paths


def evaluate(email, folder):
    user = db.row("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    if user is None:
        raise SystemExit(f"no account {email} in {db.DB_PATH}; load it with scripts/load_demo.py first")
    phrases = bank(user)
    tests = [r for r in read_manifest(folder) if r["kind"] == "test"]
    missing = sorted({r["phrase"] for r in tests} - phrases.keys())
    if not tests or missing:
        raise SystemExit("no test rows in manifest.csv" if not tests else
                         f"test rows for phrases with no enrollment in {user['language']}: {', '.join(missing)}")
    samples = [score(r, hear(r["path"], user["language"]), phrases) for r in tests]
    return samples, summarize(samples, phrases), phrases


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--folder", required=True, help="the demo folder with manifest.csv")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if gnani_mock.on():
        sys.exit("GNANI_MOCK is on: Prisma's answers would be made up, and so would these results. Unset it.")

    samples, summary, phrases = evaluate(args.email, args.folder)
    account = re.sub(r"[^a-z0-9]+", "-", args.email.lower().split("@")[0]).strip("-")
    os.makedirs(RESULTS, exist_ok=True)
    write(os.path.join(RESULTS, f"eval_{account}.csv"), summary)
    write(os.path.join(RESULTS, f"eval_{account}_samples.csv"), samples)
    print(describe(samples, phrases))
    for r in summary:
        print(f"{r['source']:>9}  {r['metric']:<13} {r['correct']:>4}/{r['n']:<4} {r['accuracy']}")
    for path in plot(account, summary, samples, phrases):
        print(f"saved {path}")
    print(f"saved {RESULTS}/eval_{account}.csv and {RESULTS}/eval_{account}_samples.csv")
