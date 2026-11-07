"""Exports rerank-v2 for the CPU: ONNX, then int8 dynamic quantization -> ml/models/rerank-v2-onnx/.

Quantization is per channel with reduce_range: the default (one scale per weight matrix, full
8-bit range) agreed with fp32 on only 16 % of val top-1 picks, per channel + reduce_range on 94 %.
Checks top-1 against the PyTorch model (on real_test.csv, and on the synthetic test sets), and
measures file size and CPU latency for one utterance: rapidfuzz over the starter bank, then the
model on its top 10. On a hybrid CPU (performance + efficiency cores) onnxruntime's default thread
count is slow, so latency is measured for a few thread counts. Writes ml/results/export.md.
"""
import os
import time

import numpy as np
import onnxruntime as ort
import pandas as pd
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModelForSequenceClassification, AutoTokenizer

import rank

SRC = os.path.join(rank.HERE, "models", "rerank-v2")
OUT = os.path.join(rank.HERE, "models", "rerank-v2-onnx")
FP32, INT8 = os.path.join(OUT, "model.onnx"), os.path.join(OUT, "model.int8.onnx")
REPORT = os.path.join(rank.HERE, "results", "export.md")
RUNS = 100
THREADS = (2, 4, 8)
CHECK_THREADS = 8  # for scoring the test sets


def onnx_scorer(path, tokenizer, threads):
    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    session = ort.InferenceSession(path, options, providers=["CPUExecutionProvider"])

    def score(heard, texts, batch=256):
        out = []
        for i in range(0, len(heard), batch):
            enc = tokenizer(heard[i:i + batch], texts[i:i + batch], padding=True, truncation=True,
                            max_length=rank.MAX_LENGTH, return_tensors="np")
            out.append(session.run(["logits"], dict(enc))[0].reshape(-1))
        return np.concatenate(out) if out else np.zeros(0)
    return score


def latency(fn):
    for _ in range(5):
        fn()
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        fn()
        times.append(1000 * (time.perf_counter() - start))
    return np.median(times), np.percentile(times, 90)


def main():
    os.makedirs(OUT, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(SRC)
    model = AutoModelForSequenceClassification.from_pretrained(SRC).eval()
    tokenizer.save_pretrained(OUT)
    enc = tokenizer(["बानी चाइए"] * 2, ["पानी चाहिए / paani chahiye"] * 2, return_tensors="pt")
    with torch.no_grad():
        torch.onnx.export(model, (enc["input_ids"], enc["attention_mask"], enc["token_type_ids"]), FP32,
                          input_names=["input_ids", "attention_mask", "token_type_ids"], output_names=["logits"],
                          dynamic_axes={n: {0: "batch", 1: "sequence"} for n in ("input_ids", "attention_mask", "token_type_ids")}
                          | {"logits": {0: "batch"}}, opset_version=17, dynamo=False)
    quantize_dynamic(FP32, INT8, weight_type=QuantType.QInt8, per_channel=True, reduce_range=True)
    sizes = {"pytorch fp32": sum(os.path.getsize(os.path.join(SRC, f)) for f in os.listdir(SRC)
                                 if f.endswith((".safetensors", ".bin"))) / 2**20,
             "onnx fp32": os.path.getsize(FP32) / 2**20, "onnx int8": os.path.getsize(INT8) / 2**20}

    # Same top-1? On real recordings if we have them, and on the synthetic test sets.
    data = rank.load_data()
    sets = {"test words": (data[(data.split == "test") & (data.source == "word")], rank.candidates(data[data.kind == "words"])),
            "test sentences": (data[(data.split == "test") & (data.source == "sentence")],
                               rank.candidates(data[data.kind == "sentences"]))}
    real_path = os.path.join(rank.HERE, "data", "real_test.csv")
    if os.path.exists(real_path):
        real = pd.read_csv(real_path, keep_default_na=False)
        sets = {"real test": (real.assign(intended_hindi=real.intended.map(rank.nfc)), rank.starter_bank()), **sets}
    # The reference is the PyTorch model as eval.py scores it (fp32, on the GPU if there is one).
    reference = AutoModelForSequenceClassification.from_pretrained(SRC).to("cuda" if torch.cuda.is_available() else "cpu").eval()
    scorers = {"pytorch": rank.torch_scorer(reference, tokenizer), "onnx int8": onnx_scorer(INT8, tokenizer, CHECK_THREADS)}
    agree = []
    for name, (rows, cands) in sets.items():
        out = {s: rank.evaluate(list(rows.heard), list(rows.intended_hindi), cands, f) for s, f in scorers.items()}
        same = np.mean([a["model_top1"] == b["model_top1"] for a, b in zip(out["pytorch"], out["onnx int8"])])
        agree.append((name, len(rows), *[rank.top_k(out[s], "model_rank", 1) for s in scorers], same))
        print(name, "done", flush=True)
    del reference
    torch.cuda.empty_cache()

    # CPU latency for one utterance against the starter bank.
    bank = rank.starter_bank()
    heard = "बानी चाइए"
    order = np.argsort(-rank.fuzz_matrix([heard], bank)[0], kind="stable")[:rank.SHORTLIST]
    texts = [rank.candidate_text(bank.hindi.iloc[i], bank.latin.iloc[i]) for i in order]
    times = {"rapidfuzz shortlist (51 phrases)": latency(lambda: rank.fuzz_matrix([heard], bank))}
    for threads in THREADS:
        torch.set_num_threads(threads)
        times[f"pytorch fp32, {threads} threads"] = latency(lambda: rank.model_scores(model, tokenizer, [heard] * 10, texts))
        for name, path in (("onnx fp32", FP32), ("onnx int8", INT8)):
            score = onnx_scorer(path, tokenizer, threads)
            times[f"{name}, {threads} threads"] = latency(lambda: score([heard] * 10, texts))
    best = min((k for k in times if k.startswith("onnx int8")), key=lambda k: times[k][0])

    md = ["# rerank-v2 CPU export", "",
          f"ONNX (opset 17), int8 dynamic quantization per channel with reduce_range (onnxruntime {ort.__version__}). "
          f"CPU: {os.cpu_count()} logical threads. Latency includes tokenizing; median and p90 of {RUNS} runs, "
          "for one heard text against rapidfuzz's top 10.", "",
          "| file | MB |", "|---|---|", *[f"| {k} | {v:.0f} |" for k, v in sizes.items()], "",
          "| step | median ms | p90 ms |", "|---|---|---|", *[f"| {k} | {m:.0f} | {p:.0f} |" for k, (m, p) in times.items()], "",
          f"Fastest int8 setting: **{best}**, {times[best][0]:.0f} ms median for the model, plus "
          f"{times['rapidfuzz shortlist (51 phrases)'][0]:.0f} ms for the rapidfuzz shortlist.", "",
          "| set | n | top-1 pytorch (as in eval.py) | top-1 onnx int8 (CPU) | same top-1 |", "|---|---|---|---|---|",
          *[f"| {n} | {k} | {100 * a:.1f} | {100 * b:.1f} | {100 * s:.1f} % |" for n, k, a, b, s in agree], ""]
    if "real test" not in sets:
        md += ["real_test.csv doesn't exist yet: run this again after run_real_test.py to check the real recordings.", ""]
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
