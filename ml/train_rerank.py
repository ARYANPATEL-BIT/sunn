"""Trains the correction model: a MuRIL cross-encoder that scores (what Prisma heard, a candidate).

    uv run train_rerank.py --sources both        # rerank-v2
    uv run train_rerank.py --sources words       # ablation: word rows only
    uv run train_rerank.py --sources sentences   # ablation: sentence + composed rows only

Input "heard [SEP] candidate_hindi / candidate_latin". Each example is a group of 8: the intended
text and 7 wrong ones from the same pool (words, or sentences), trained with a softmax over the
group (label 1 for the intended, 0 for the rest). The 7 are 4 hard ones, 2 of the same category
and 1 of similar length. From epoch 2 the hard ones are the current model's mistakes first (wrong
candidates in rapidfuzz's top 10 that it scores at least as high as the intended), topped up with
the closest by rapidfuzz. Pools hold train intended texts only.

Batches are half word rows and half sentence rows when training on both. Epoch 1 uses clean and
mild rows only; later epochs use everything. The best epoch by val score (the mean of val top-1
on words and on sentences, rapidfuzz top 10 reordered) is saved; training stops after PATIENCE
epochs that don't improve it. Patience 1 stopped runs at the dip right after the switch from the
easy epoch to all rows, so the ablation would have compared stopping luck, not data.
"""
import argparse
import csv
import json
import os
import random
import time

import numpy as np
import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

import rank

SEED = 7
LR = 2e-5
WARMUP = 0.05
PATIENCE = 2  # epochs without a better val score before stopping
BATCH_SIZES = (32, 16, 8)  # groups per step; the next one is used if the GPU runs out of memory
HARD, SAME_CATEGORY, SIMILAR_LENGTH = 4, 2, 1
GROUP = 1 + HARD + SAME_CATEGORY + SIMILAR_LENGTH
LOG = os.path.join(rank.HERE, "results", "train_log.csv")
LOG_FIELDS = ["run", "epoch", "rows", "train_loss", "val_top1_words", "val_top1_sentences", "val_score",
              "rapidfuzz_val_top1_words", "rapidfuzz_val_top1_sentences", "batch_size", "seconds"]


class Source:
    """One candidate pool (words or sentences): its train rows, candidates and rapidfuzz matrix."""

    def __init__(self, rows):
        self.rows = rows.reset_index(drop=True)
        self.cands = rank.candidates(rows)
        self.texts = [rank.candidate_text(h, l) for h, l in zip(self.cands.hindi, self.cands.latin)]
        index = {h: i for i, h in enumerate(self.cands.hindi)}
        self.target = np.array([index[h] for h in self.rows.intended_hindi])
        fuzz = rank.fuzz_matrix(list(self.rows.heard), self.cands)
        fuzz[np.arange(len(self.rows)), self.target] = -1  # never pick the intended as a negative
        self.closest = np.argsort(-fuzz, axis=1, kind="stable")
        self.by_category = {c: list(g) for c, g in self.cands.reset_index(drop=True).groupby("category").groups.items()}
        self.length = self.cands.hindi.str.len().to_numpy()

    def mine(self, rng, model=None, tokenizer=None):
        """7 negatives (candidate indexes) per row."""
        mistakes = [[] for _ in self.rows.index]
        if model is not None:
            short = self.closest[:, :rank.SHORTLIST]
            heard = [h for h in self.rows.heard for _ in range(rank.SHORTLIST + 1)]
            texts = [self.texts[i] for t, s in zip(self.target, short) for i in [t, *s]]
            scores = rank.model_scores(model, tokenizer, heard, texts).reshape(len(self.rows), rank.SHORTLIST + 1)
            for r, (s, cand) in enumerate(zip(scores, short)):
                beat = [int(c) for c, v in sorted(zip(cand, s[1:]), key=lambda x: -x[1]) if v >= s[0]]
                mistakes[r] = beat[:HARD]
        negatives = []
        for r, target in enumerate(self.target):
            chosen = list(mistakes[r])
            for i in self.closest[r]:  # top up with the closest by rapidfuzz
                if len(chosen) == HARD:
                    break
                if i not in chosen:
                    chosen.append(int(i))
            same = [i for i in self.by_category[self.cands.category.iloc[target]] if i != target and i not in chosen]
            chosen += rng.sample(same, min(SAME_CATEGORY, len(same)))
            gap = np.abs(self.length - self.length[target]).astype(float)
            gap[[target, *chosen]] = np.inf
            chosen += [int(i) for i in rng.sample(list(np.argsort(gap, kind="stable")[:5]), SIMILAR_LENGTH)]
            for i in self.closest[r]:  # a small category: fill with the next closest
                if len(chosen) == GROUP - 1:
                    break
                if i not in chosen:
                    chosen.append(int(i))
            negatives.append(chosen)
        return negatives


def validate(val, score_fn=None):
    """{"words": top-1, "sentences": top-1} on val, candidates = every intended text of that kind."""
    result = {}
    for kind, (rows, cands) in val.items():
        out = rank.evaluate(list(rows.heard), list(rows.intended_hindi), cands, score_fn)
        result[kind] = rank.top_k(out, "model_rank" if score_fn else "fuzz_rank", 1)
    return result


def write_log(run, rows):
    old = []
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as f:
            old = [r for r in csv.DictReader(f) if r.get("run") not in (None, run)]
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        writer.writeheader()
        writer.writerows(old + rows)


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--sources", choices=["words", "sentences", "both"], default="both")
    args.add_argument("--epochs", type=int, default=5)
    args = args.parse_args()
    run = "rerank-v2" if args.sources == "both" else f"ablation-{args.sources}"
    out = os.path.join(rank.HERE, "models", run)

    rng = random.Random(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if not torch.cuda.is_available():
        raise SystemExit("no CUDA GPU: run ml/check_gpu.py")
    torch.cuda.set_per_process_memory_fraction(0.9)  # Windows otherwise spills into system RAM

    data = rank.load_data()
    kinds = ["words", "sentences"] if args.sources == "both" else [args.sources]
    sources = {k: Source(data[(data.split == "train") & (data.kind == k)]) for k in kinds}
    # Val candidates are every intended text of the kind, as at test time.
    val = {k: (data[(data.split == "val") & (data.kind == k)], rank.candidates(data[data.kind == k]))
           for k in ("words", "sentences")}
    baseline = validate(val)
    for k, s in sources.items():
        print(f"{k}: {len(s.rows)} train rows, pool of {len(s.cands)} train intended texts")
    print("rapidfuzz val top-1:", {k: round(v, 3) for k, v in baseline.items()}, flush=True)

    tokenizer = AutoTokenizer.from_pretrained(rank.MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(rank.MODEL_NAME, num_labels=1).cuda()
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.01)

    easy = {k: np.flatnonzero(s.rows.severity.isin(["clean", "mild"])) for k, s in sources.items()}
    full = {k: np.arange(len(s.rows)) for k, s in sources.items()}
    per_epoch = lambda pick: len(kinds) * max(len(v) for v in pick.values())  # groups, the smaller source cycled
    planned = per_epoch(easy) + (args.epochs - 1) * per_epoch(full)
    batch, seen, best, waited, log_rows, started_run = BATCH_SIZES[0], 0, -1.0, 0, [], time.time()

    for epoch in range(1, args.epochs + 1):
        started = time.time()
        model.eval()
        negatives = {k: s.mine(rng, None if epoch == 1 else model, tokenizer) for k, s in sources.items()}
        model.train()
        pick = easy if epoch == 1 else full
        n = max(len(v) for v in pick.values())
        # Each source's rows in a fresh order, the smaller one repeated to the larger one's length.
        queues = {k: np.concatenate([np.random.permutation(v) for _ in range(-(-n // len(v)))])[:n]
                  for k, v in pick.items()}
        losses, at = [], 0
        while at < n:
            take = batch // len(kinds)
            groups = [(k, int(r)) for k in kinds for r in queues[k][at:at + take]]
            heard = [sources[k].rows.heard[r] for k, r in groups for _ in range(GROUP)]
            texts = [sources[k].texts[i] for k, r in groups for i in [sources[k].target[r], *negatives[k][r]]]
            for g in optimizer.param_groups:  # 5 % linear warmup, then linear decay to 0
                g["lr"] = LR * max(0.0, min(seen / (WARMUP * planned), (planned - seen) / ((1 - WARMUP) * planned)))
            try:
                enc = tokenizer(heard, texts, padding=True, truncation=True, max_length=rank.MAX_LENGTH,
                                return_tensors="pt").to("cuda")
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    logits = model(**enc).logits.float().view(len(groups), GROUP)
                loss = F.cross_entropy(logits, torch.zeros(len(groups), dtype=torch.long, device="cuda"))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
            except torch.cuda.OutOfMemoryError:
                optimizer.zero_grad(set_to_none=True)
                torch.cuda.empty_cache()
                smaller = [b for b in BATCH_SIZES if b < batch]
                if not smaller:
                    raise
                batch = smaller[0]
                print(f"out of GPU memory: batch {batch} from now on", flush=True)
                continue
            losses.append(loss.item())
            at += take
            seen += len(groups)
            if len(losses) % 50 == 0:
                print(f"  epoch {epoch} step {len(losses)} loss {np.mean(losses[-50:]):.4f}", flush=True)

        model.eval()
        result = validate(val, rank.torch_scorer(model, tokenizer, bf16=True))
        model.train()
        score = (result["words"] + result["sentences"]) / 2
        seconds = round(time.time() - started)
        log_rows.append({"run": run, "epoch": epoch, "rows": n * len(kinds), "train_loss": round(float(np.mean(losses)), 4),
                         "val_top1_words": round(result["words"], 4), "val_top1_sentences": round(result["sentences"], 4),
                         "val_score": round(score, 4), "rapidfuzz_val_top1_words": round(baseline["words"], 4),
                         "rapidfuzz_val_top1_sentences": round(baseline["sentences"], 4), "batch_size": batch,
                         "seconds": seconds})
        write_log(run, log_rows)
        print(f"epoch {epoch}: loss {np.mean(losses):.4f}, val top-1 words {result['words']:.3f}"
              f" (rapidfuzz {baseline['words']:.3f}), sentences {result['sentences']:.3f}"
              f" (rapidfuzz {baseline['sentences']:.3f}), score {score:.4f}, {seconds} s,"
              f" peak GPU {torch.cuda.max_memory_allocated() / 2**30:.1f} GiB", flush=True)
        if score > best:
            best, best_epoch, waited = score, epoch, 0
            model.save_pretrained(out)
            tokenizer.save_pretrained(out)
            info = {"run": run, "sources": args.sources, "base": rank.MODEL_NAME, "best_epoch": epoch,
                    "val_top1": result, "val_score": score, "rapidfuzz_val_top1": baseline, "lr": LR, "patience": PATIENCE,
                    "batch_size": batch, "seed": SEED, "train_rows": {k: len(s.rows) for k, s in sources.items()}}
            print(f"  saved to {out}", flush=True)
        else:
            waited += 1
            print(f"  val score did not improve ({waited} of {PATIENCE})", flush=True)
            if waited == PATIENCE:
                break
    info.update(epochs_run=epoch, train_minutes=round((time.time() - started_run) / 60, 1))
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    print(f"{run}: {epoch} epochs in {info['train_minutes']} min, best epoch {best_epoch}, val score {best:.4f}")


if __name__ == "__main__":
    main()
