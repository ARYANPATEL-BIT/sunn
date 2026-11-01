"""Fine-tune whisper-small with LoRA on the TRAIN speakers of training/splits.json.

LoRA (r=16, alpha=32, dropout 0.05) on the q and v projections of every attention layer, in
the encoder and the decoder; everything else stays frozen. Each clip is decoded with its own
language token (hindi or english) and task transcribe. bf16 autocast, gradient checkpointing,
batches of 8 with gradient accumulation to 32 (on running out of GPU memory the batch halves and
the accumulation doubles). A few clips of the train speakers are kept back as a validation set;
every --eval-every steps their CER is measured and the best adapter so far is saved.

Writes models/shared/<run>/ (the adapter, run.json with the settings, the split and the git
commit) and training/runs/<run>.csv (step, loss, learning rate, batch, validation CER).

    uv run --group train training/train.py --exports data/export-1 --torgo data/torgo --run-name first
"""
import argparse
import csv
import functools
import json
import os
import random
import subprocess
import sys
import time
import unicodedata

import jiwer
import numpy as np
import torch
from peft import LoraConfig, get_peft_model
from transformers import WhisperForConditionalGeneration, WhisperProcessor, get_linear_schedule_with_warmup

import data

BASE = "openai/whisper-small"
LANGUAGES = {"hi": "hindi", "en": "english"}
BATCH, EFFECTIVE_BATCH = 8, 32
LR, WARMUP = 1e-4, 200
VAL_SHARE, VAL_MAX = 0.05, 200  # of the train speakers' clips, kept back for validation
# Of the GPU's memory, for PyTorch. On Windows the driver can spill into system RAM instead of
# running out, and training then crawls; with a cap it runs out properly, and the batch shrinks.
MEMORY_FRACTION = 0.9
LORA = {"r": 16, "lora_alpha": 32, "lora_dropout": 0.05, "target_modules": ["q_proj", "v_proj"]}


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
                              cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def normalize(text):
    """For CER and WER: NFC (so a nukta letter compares equal however it was typed), lower case,
    punctuation (the danda too) out, spaces collapsed. Devanagari stays Devanagari."""
    text = unicodedata.normalize("NFC", text.lower())
    return " ".join("".join(c if unicodedata.category(c)[0] in "LNM" else " " for c in text).split())


def example(clip, processor, rng=None):
    """Model inputs for one clip: log-mel features, and the token ids <|startoftranscript|>
    <|hi or en|> <|transcribe|> <|notimestamps|> text <|endoftext|>. rng augments (train only)."""
    samples = data.load_audio(clip["path"])
    if rng is not None:
        samples = data.augment(samples, rng)
    features = processor.feature_extractor(samples, sampling_rate=data.RATE, return_tensors="np").input_features[0]
    processor.tokenizer.set_prefix_tokens(language=LANGUAGES[clip["language"]], task="transcribe", predict_timestamps=False)
    return features, processor.tokenizer(clip["text"]).input_ids


def collate(examples, pad_id):
    """Teacher forcing: the decoder reads ids[:-1] and learns ids[1:]; padding is ignored (-100)."""
    width = max(len(ids) for _, ids in examples) - 1
    inputs = torch.full((len(examples), width), pad_id)
    labels = torch.full((len(examples), width), -100)
    for i, (_, ids) in enumerate(examples):
        inputs[i, :len(ids) - 1], labels[i, :len(ids) - 1] = torch.tensor(ids[:-1]), torch.tensor(ids[1:])
    return torch.tensor(np.stack([f for f, _ in examples])), inputs, labels


class Clips(torch.utils.data.Dataset):
    """Training examples, augmented afresh every time. The augmentation's seed comes from torch's
    generator (seeded in the main process, and per worker by the DataLoader), so it changes from
    one epoch to the next and still follows the run's seed."""

    def __init__(self, clips, processor):
        self.clips, self.processor = clips, processor

    def __len__(self):
        return len(self.clips)

    def __getitem__(self, i):
        return example(self.clips[i], self.processor, np.random.default_rng(int(torch.randint(2**31, ()))))


def batches(dataset, size, workers, pad_id):
    """Shuffled training batches, forever. The workers stay up between epochs, because starting
    them is slow on Windows; if they fail, as they can on Windows, it goes on with num_workers=0."""
    loader = None
    while True:
        if loader is None:
            loader = torch.utils.data.DataLoader(dataset, batch_size=size, shuffle=True, num_workers=workers,
                                                 persistent_workers=workers > 0,
                                                 collate_fn=functools.partial(collate, pad_id=pad_id))
        try:
            yield from loader
        except Exception as error:  # noqa: BLE001 (pickling, spawn and pipe errors all look different)
            if not workers:
                raise
            print(f"DataLoader workers failed ({error}); using num_workers=0")
            workers, loader = 0, None


@torch.no_grad()
def transcribe(model, processor, clips, batch=16):
    """Greedy transcripts, each clip decoded with its own language forced."""
    model.eval()
    out = {}
    for language in sorted({c["language"] for c in clips}):
        group = [c for c in clips if c["language"] == language]
        for start in range(0, len(group), batch):
            chunk = group[start:start + batch]
            features = processor.feature_extractor([data.load_audio(c["path"]) for c in chunk], sampling_rate=data.RATE,
                                                   return_tensors="pt").input_features.to("cuda")
            with torch.autocast("cuda", dtype=torch.bfloat16):
                ids = model.generate(input_features=features, language=LANGUAGES[language], task="transcribe",
                                     max_new_tokens=128, use_cache=True)
            for clip, text in zip(chunk, processor.batch_decode(ids, skip_special_tokens=True,
                                                                          clean_up_tokenization_spaces=False)):
                out[clip["path"]] = text.strip()
    model.train()
    return out


def cer(clips, hypotheses):
    """Character error rate over all clips, normalized; 1.0 when every reference is empty."""
    refs = [normalize(c["text"]) for c in clips]
    hyps = [normalize(hypotheses[c["path"]]) for c in clips]
    kept = [(r, h) for r, h in zip(refs, hyps) if r]
    return jiwer.cer([r for r, _ in kept], [h for _, h in kept]) if kept else 1.0


def load_model(gradient_checkpointing=True):
    model = WhisperForConditionalGeneration.from_pretrained(BASE)
    model.generation_config.forced_decoder_ids = None  # the language comes from each clip
    if gradient_checkpointing:
        # Non-reentrant, so the frozen encoder input doesn't cut the LoRA weights off from the gradient.
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.config.use_cache = False
    return get_peft_model(model, LoraConfig(**LORA)).to("cuda")


def train(args):
    if not torch.cuda.is_available():
        raise SystemExit("torch.cuda.is_available() is False: install the train group (uv sync --group train)"
                         " on a machine with an NVIDIA GPU")
    torch.cuda.set_per_process_memory_fraction(MEMORY_FRACTION)
    seed_everything(args.seed)
    clips = data.collect(args.exports, args.torgo, args.include_simulated)
    splits = data.split(clips)
    data.report(clips, splits)
    pool = [c for c in clips if c["speaker"] in splits["train"]]
    random.Random(args.seed).shuffle(pool)
    n_val = min(VAL_MAX, max(1, round(VAL_SHARE * len(pool)))) if len(pool) > 1 else 0
    val, train_clips = pool[:n_val], pool[n_val:]
    if not train_clips:
        raise SystemExit("no training clips")
    print(f"training on {len(train_clips)} clips, validating on {n_val} clips of the train speakers")

    processor = WhisperProcessor.from_pretrained(BASE)
    model = load_model()
    model.print_trainable_parameters()
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=LR)
    schedule = get_linear_schedule_with_warmup(optimizer, min(WARMUP, args.steps // 10), args.steps)
    dataset = Clips(train_clips, processor)
    pad_id = processor.tokenizer.eos_token_id

    out = os.path.join("models", "shared", args.run_name)
    os.makedirs(out, exist_ok=True)
    os.makedirs(os.path.join("training", "runs"), exist_ok=True)
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as f:
        json.dump({"base": BASE, "lora": LORA, "lr": LR, "warmup": WARMUP, "steps": args.steps,
                   "effective_batch": EFFECTIVE_BATCH, "seed": args.seed, "exports": args.exports, "torgo": args.torgo,
                   "include_simulated": args.include_simulated, "train_clips": len(train_clips),
                   "val_clips": [c["path"] for c in val], "splits": splits, "git_sha": git_sha()},
                  f, indent=2, ensure_ascii=False)
    log = open(os.path.join("training", "runs", f"{args.run_name}.csv"), "w", newline="", encoding="utf-8")
    writer = csv.writer(log)
    writer.writerow(["step", "loss", "lr", "batch", "val_cer", "seconds"])

    size, best, start = BATCH, None, time.time()
    stream = batches(dataset, size, args.workers, pad_id)
    step = 0
    model.train()
    while step < args.steps:
        try:
            total = 0.0
            for _ in range(EFFECTIVE_BATCH // size):
                features, inputs, labels = (t.to("cuda") for t in next(stream))
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    loss = model(input_features=features, decoder_input_ids=inputs, labels=labels).loss
                (loss * size / EFFECTIVE_BATCH).backward()
                total += loss.item() * size / EFFECTIVE_BATCH
        except torch.cuda.OutOfMemoryError:
            optimizer.zero_grad(set_to_none=True)
            torch.cuda.empty_cache()
            if size == 1:
                raise
            size //= 2
            print(f"out of GPU memory: batch {size}, accumulating {EFFECTIVE_BATCH // size} for {EFFECTIVE_BATCH}")
            stream = batches(dataset, size, args.workers, pad_id)
            continue
        if not np.isfinite(total):
            raise SystemExit(f"loss is {total} at step {step + 1}; stopping")
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        optimizer.step()
        schedule.step()
        optimizer.zero_grad(set_to_none=True)
        step += 1

        val_cer = ""
        if val and (step % args.eval_every == 0 or step == args.steps):
            val_cer = cer(val, transcribe(model, processor, val))
            if best is None or val_cer < best:
                best = val_cer
                model.save_pretrained(out)
        writer.writerow([step, f"{total:.4f}", f"{schedule.get_last_lr()[0]:.2e}", size,
                         f"{val_cer:.4f}" if val_cer != "" else "", round(time.time() - start)])
        log.flush()
        if step % 10 == 0 or val_cer != "":
            print(f"step {step}/{args.steps}  loss {total:.3f}  batch {size}"
                  + (f"  val CER {val_cer:.3f} (best {best:.3f})" if val_cer != "" else ""))
    if not val:
        model.save_pretrained(out)  # nothing to choose the best by: keep the last
    log.close()
    print(f"saved the adapter (best val CER {best if best is not None else 'n/a'}) to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--exports", nargs="*", default=[], help="folders with metadata.csv")
    parser.add_argument("--torgo", help="the TORGO folder, e.g. data/torgo")
    parser.add_argument("--steps", type=int, default=4000)
    parser.add_argument("--run-name", default=time.strftime("run-%Y%m%d-%H%M"))
    parser.add_argument("--include-simulated", action="store_true")
    parser.add_argument("--eval-every", type=int, default=250)
    parser.add_argument("--workers", type=int, default=2, help="DataLoader workers (0 if they fail on Windows)")
    parser.add_argument("--seed", type=int, default=data.SEED)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    train(args)
