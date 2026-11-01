"""Evaluate a shared-model run on its HELD-OUT speakers only (the test speakers in its run.json).

Systems, on the same clips:
    zero-shot     openai/whisper-small, each clip decoded with its language forced
    fine-tuned    the same with the run's LoRA adapter
    prisma        Gnani Prisma's raw transcript. Cached transcripts are reused; at most
                  --max-gnani-calls uncached clips are sent, and the number sent is reported

Transcript metrics (corpus level, after normalizing: lower case, punctuation out, spaces
collapsed): CER for Hindi (Devanagari, so a romanized transcript counts as wrong), WER and CER
for English.

Phrase top-1, which is what matters in the app. A clip is correct when its own phrase scores
strictly highest (a tie counts as a miss, and so does an empty transcript):
    <system> -> phrase text   the transcript matched against the texts of the speaker's own
                              phrases with matcher.similarity
    sunn                      today's pipeline: the Prisma transcript ranked by matcher.rank against
                              the Prisma transcripts of the speaker's OTHER recordings (leave one
                              out), as the app ranks against enrollment recordings. Only clips whose
                              phrase has another recording with a Prisma transcript
    sunn + <model>            on the same clips, each phrase's score plus MODEL_WEIGHT × the model
                              transcript's similarity to the phrase text. MODEL_WEIGHT is fixed
                              here, not tuned: tuning it on the test speakers would flatter it

The gate passes only if the fine-tuned model beats zero-shot on every held-out language (Hindi
CER, English WER) AND sunn + fine-tuned beats sunn's top-1 by at least GATE_POINTS points.

Writes results/shared_model_eval.csv (every number), results/shared_model_eval_samples.csv
(every clip and transcript: check consent before publishing it) and results/shared_model_eval.png.

    uv run --group train training/evaluate.py --run-name first --exports data/export-1 --torgo data/torgo
"""
import argparse
import csv
import json
import os
import sys
import tempfile

import jiwer
import matplotlib
import torch
from peft import PeftModel
from transformers import WhisperForConditionalGeneration, WhisperProcessor

matplotlib.use("Agg")  # files only, no window
import matplotlib.pyplot as plt  # noqa: E402

import data  # noqa: E402
import train  # noqa: E402

sys.path.insert(1, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
import audio  # noqa: E402
import gnani  # noqa: E402
import gnani_mock  # noqa: E402
import matcher  # noqa: E402
import prisma  # noqa: E402

RESULTS = "results"
MODEL_WEIGHT = 1.0  # the model's similarity counts as much as Prisma's, decided before seeing results
GATE_POINTS = 5
PRIMARY = {"hi": "cer", "en": "wer"}
# The palette of scripts/evaluate.py (the dataviz skill's slots 1-3, validated as a set); labels carry the values.
COLORS = {"zero-shot": "#2a78d6", "fine-tuned": "#eb6834", "prisma": "#1baf7a"}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e5e4e0", "#fcfcfb"


def whisper(adapter=None):
    model = WhisperForConditionalGeneration.from_pretrained(train.BASE)
    model.generation_config.forced_decoder_ids = None
    return (PeftModel.from_pretrained(model, adapter) if adapter else model).to("cuda")


def hear(clips, limit):
    """{path: Prisma transcript} for the clips Prisma has heard (cached) or that could still be
    sent (at most limit); returns it and the number sent. Each clip is converted exactly as the
    app converts an upload, so a recording made in the app hits its cached transcript."""
    heard, sent = {}, 0
    with tempfile.TemporaryDirectory() as folder:
        for i, clip in enumerate(clips):
            wav = os.path.join(folder, f"{i}.wav")
            audio.to_wav(clip["path"], wav)
            with open(wav, "rb") as f:
                cached = os.path.exists(prisma.cache_path(f.read(), clip["language"]))
            if not cached and sent >= limit:
                continue
            try:
                heard[clip["path"]] = prisma.transcribe(wav, clip["language"])
            except gnani.GnaniError as error:
                print(f"Prisma failed ({error.detail}); sending nothing more")
                limit = sent
                continue
            sent += not cached
    print(f"Prisma: {len(heard)} of {len(clips)} clips, {sent} Gnani calls sent, {len(heard) - sent} from the cache")
    return heard, sent


def error_rates(clips, hypotheses):
    """[(language, metric, value, n)] over the clips that have a hypothesis."""
    rows = []
    for language in sorted({c["language"] for c in clips}):
        pairs = [(train.normalize(c["text"]), train.normalize(hypotheses[c["path"]]))
                 for c in clips if c["language"] == language and c["path"] in hypotheses]
        pairs = [(r, h) for r, h in pairs if r]
        if not pairs:
            continue
        refs, hyps = [r for r, _ in pairs], [h for _, h in pairs]
        rows.append((language, "cer", jiwer.cer(refs, hyps), len(pairs)))
        if language == "en":
            rows.append((language, "wer", jiwer.wer(refs, hyps), len(pairs)))
    return rows


def unique_top(scores, answer):
    """1 when answer has the highest score and nothing ties it."""
    best = max(scores.values())
    return int(scores.get(answer) == best and sum(s == best for s in scores.values()) == 1)


def to_text(clip, hypothesis, phrases):
    """Phrase top-1 of a transcript matched straight to the speaker's phrase texts."""
    if not hypothesis.strip():
        return 0
    return unique_top({p: matcher.similarity(hypothesis, p) for p in phrases}, clip["text"])


def fingerprints(clip, clips, heard):
    """{phrase: [Prisma transcripts of the speaker's other recordings of it]}, like enrollment."""
    found = {}
    for other in clips:
        if other["speaker"] == clip["speaker"] and other["path"] != clip["path"] and other["path"] in heard:
            found.setdefault(other["text"], []).append(heard[other["path"]])
    return found


def sunn(clip, hypothesis, bank, model_hypothesis=None):
    """Phrase top-1 of Sunn's ranking (matcher.rank), plus MODEL_WEIGHT × the model transcript's
    similarity to each phrase's text when there is one."""
    if not hypothesis.strip():
        return 0
    candidates = [{"key": text, "fingerprints": prints, "contexts": ["any"]} for text, prints in bank.items()]
    scores = {c["key"]: c["score"] for c in matcher.rank(hypothesis, candidates, k=len(candidates))}
    if model_hypothesis is not None and model_hypothesis.strip():
        scores = {p: s + MODEL_WEIGHT * matcher.similarity(model_hypothesis, p) for p, s in scores.items()}
    return unique_top(scores, clip["text"])


def phrase_rows(clips, transcripts, heard):
    """[(system, top-1 correct, n)] and one dict per clip with what each system got."""
    samples = []
    for clip in clips:
        phrases = sorted({c["text"] for c in clips if c["speaker"] == clip["speaker"]})
        row = {"speaker": clip["speaker"], "language": clip["language"], "source": clip["source"], "text": clip["text"],
               "phrases": len(phrases), **{f"{s} transcript": t.get(clip["path"], "") for s, t in transcripts.items()}}
        for system, hypotheses in transcripts.items():
            if clip["path"] in hypotheses:
                row[f"{system} -> phrase text"] = to_text(clip, hypotheses[clip["path"]], phrases)
        bank = fingerprints(clip, clips, heard)
        if clip["path"] in heard and clip["text"] in bank:
            row["sunn"] = sunn(clip, heard[clip["path"]], bank)
            for system in ("zero-shot", "fine-tuned"):
                row[f"sunn + {system}"] = sunn(clip, heard[clip["path"]], bank, transcripts[system][clip["path"]])
        samples.append(row)
    systems = [f"{s} -> phrase text" for s in transcripts] + ["sunn", "sunn + zero-shot", "sunn + fine-tuned"]
    return [(s, sum(r[s] for r in samples if s in r), sum(s in r for r in samples)) for s in systems], samples


def describe(clips, speakers):
    part = [c for c in clips if c["speaker"] in speakers]
    by_language = ", ".join(f"{lang} {len({c['speaker'] for c in part if c['language'] == lang})}"
                            for lang in sorted({c["language"] for c in part}))
    return (f"{len(speakers)} speakers ({by_language}), {len(part)} clips, "
            f"{sum(c['seconds'] for c in part) / 60:.1f} min, from {', '.join(sorted({c['source'] for c in part}))}")


def plot(path, summary, phrase, title):
    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 4.8), facecolor=SURFACE, gridspec_kw={"width_ratios": [1, 1.4]})
    groups = [(lang, m) for lang, m in [("hi", "cer"), ("en", "cer"), ("en", "wer")]
              if any(r["language"] == lang and r["metric"] == m for r in summary)]
    find = {(r["system"], r["language"], r["metric"]): r for r in summary}
    width = 0.26
    for i, system in enumerate(COLORS):
        xs = [j + (i - 1) * width for j in range(len(groups))]
        rows = [find.get((system, lang, m)) for lang, m in groups]
        drawn = left.bar(xs, [float(r["value"]) if r else 0 for r in rows], width - 0.03, label=system, color=COLORS[system])
        left.bar_label(drawn, [f"{float(r['value']):.2f}" if r else "n/a" for r in rows], fontsize=8, color=MUTED, padding=2)
    left.set_xticks(range(len(groups)), [f"{lang} {m.upper()}\n(n={find[('zero-shot', lang, m)]['n']})" for lang, m in groups])
    top = max([float(r["value"]) for r in summary if r["metric"] in ("cer", "wer")] + [1])
    left.set_ylim(0, top * 1.15)
    left.set_title("Error rate (lower is better)", loc="left", fontsize=10, color=INK)
    left.legend(frameon=False, ncols=3, loc="upper left", bbox_to_anchor=(0, -0.14))

    # Every system, measured or not (n/a: no Prisma transcripts to measure it on).
    drawn = right.bar(range(len(phrase)), [c / n if n else 0 for _, c, n in phrase], 0.6, color=MUTED)
    right.bar_label(drawn, [f"{c}/{n}" if n else "n/a" for _, c, n in phrase], fontsize=8, color=MUTED, padding=2)
    right.set_xticks(range(len(phrase)), [s.replace(" -> ", "\n-> ").replace("sunn + ", "sunn +\n") for s, _, _ in phrase],
                     fontsize=8)
    right.set_ylim(0, 1.15)
    right.set_title("Phrase top-1 (higher is better)", loc="left", fontsize=10, color=INK)
    for ax in (left, right):
        ax.set_facecolor(SURFACE)
        ax.grid(axis="y", color=GRID)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(title, x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def gate(summary, phrase):
    """(passed, [reasons]) for the rule at the top of this file."""
    find = {(r["system"], r["language"], r["metric"]): float(r["value"]) for r in summary}
    reasons, passed = [], True
    for language in sorted({r["language"] for r in summary if r["system"] == "zero-shot"}):
        metric = PRIMARY[language]
        zero, tuned = find[("zero-shot", language, metric)], find[("fine-tuned", language, metric)]
        better = tuned < zero
        passed &= better
        reasons.append(f"{language} {metric.upper()}: fine-tuned {tuned:.3f} vs zero-shot {zero:.3f} "
                       f"({'better' if better else 'NOT better'})")
    tops = {s: (c, n) for s, c, n in phrase}
    (base, n), (fused, _) = tops["sunn"], tops["sunn + fine-tuned"]
    if not n:
        passed = False
        reasons.append("phrase top-1: no clip has both a Prisma transcript and another recording of its phrase, so "
                       "Sunn's pipeline couldn't be measured")
    else:
        gain = 100 * (fused - base) / n
        passed &= gain >= GATE_POINTS
        reasons.append(f"phrase top-1: sunn {base}/{n} ({100 * base / n:.1f} %), sunn + fine-tuned {fused}/{n} "
                       f"({100 * fused / n:.1f} %): {gain:+.1f} points, {'at least' if gain >= GATE_POINTS else 'under'} "
                       f"the {GATE_POINTS} needed")
    return passed, reasons


def write(path, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def evaluate(args):
    if not torch.cuda.is_available():
        raise SystemExit("torch.cuda.is_available() is False: install the train group (uv sync --group train)")
    if gnani_mock.on():
        raise SystemExit("GNANI_MOCK is on: Prisma's answers would be made up, and so would these results. Unset it.")
    adapter = os.path.join("models", "shared", args.run_name)
    with open(os.path.join(adapter, "run.json"), encoding="utf-8") as f:
        run = json.load(f)
    clips = data.collect(args.exports, args.torgo, run["include_simulated"])
    test = [c for c in clips if c["speaker"] in run["splits"]["test"]]
    if not test:
        raise SystemExit("none of the run's held-out speakers are in these clips")
    data.report(clips, run["splits"])

    processor = WhisperProcessor.from_pretrained(train.BASE)
    transcripts = {}
    for system, path in (("zero-shot", None), ("fine-tuned", adapter)):
        model = whisper(path)
        transcripts[system] = train.transcribe(model, processor, test)
        del model
        torch.cuda.empty_cache()
    heard, sent = hear(test, args.max_gnani_calls)
    transcripts["prisma"] = heard

    summary = [{"system": s, "language": lang, "metric": m, "value": f"{v:.4f}", "n": n}
               for s, t in transcripts.items() for lang, m, v, n in error_rates(test, t)]
    phrase, samples = phrase_rows(test, transcripts, heard)
    summary += [{"system": s, "language": "all", "metric": "phrase_top1", "value": f"{c / n:.4f}" if n else "", "n": n}
                for s, c, n in phrase]
    summary.append({"system": "prisma", "language": "all", "metric": "gnani_calls_sent", "value": sent, "n": len(test)})

    os.makedirs(RESULTS, exist_ok=True)
    write(os.path.join(RESULTS, "shared_model_eval.csv"), summary)
    write(os.path.join(RESULTS, "shared_model_eval_samples.csv"), samples)
    title = (f"Shared whisper-small + LoRA ({args.run_name}) on held-out speakers only: {describe(clips, run['splits']['test'])}\n"
             f"Train speakers: {describe(clips, run['splits']['train'])}. Prisma: {len(heard)} of {len(test)} clips, "
             f"{sent} Gnani calls sent")
    plot(os.path.join(RESULTS, "shared_model_eval.png"), summary, phrase, title)
    for r in summary:
        print(f"{r['system']:>28}  {r['language']:<3} {r['metric']:<16} {r['value']:>8}  n={r['n']}")
    print(f"saved {RESULTS}/shared_model_eval.csv, {RESULTS}/shared_model_eval_samples.csv and {RESULTS}/shared_model_eval.png")

    passed, reasons = gate([r for r in summary if r["metric"] in ("cer", "wer")], phrase)
    print(f"\nGATE: {'PASSED, app integration can go ahead' if passed else 'NOT PASSED, the shared model stays research'}")
    for reason in reasons:
        print(f"  - {reason}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", required=True, help="the run under models/shared/")
    parser.add_argument("--exports", nargs="*", default=[], help="the folders the run was trained from")
    parser.add_argument("--torgo", help="the TORGO folder, if the run used it")
    parser.add_argument("--max-gnani-calls", type=int, default=200, help="uncached clips sent to Prisma, at most")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    evaluate(args)
