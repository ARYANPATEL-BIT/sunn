"""The trained reranker (RERANKER_ENABLED): rerank-v2, the MuRIL cross-encoder in ml/, as one
more weighted part of the matcher's score. It scores the matcher's top SHORTLIST, as it was trained
and evaluated (ml/rank.py), and its part is RERANKER_WEIGHT × its softmax probability over them.

The ONNX model loads once, at startup; onnxruntime is imported only when this is on. A missing
model or package, or a failure while scoring, is one warning, and the app goes on without it."""
import logging
import os
import sys

import numpy as np

import log
import matcher

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "ml", "models", "rerank-v2-onnx", "model.onnx")
SHORTLIST = 10
MAX_LENGTH = 64  # tokens per (heard, candidate) pair, as in training
DEFAULT_WEIGHT = 20  # a confident pick can overturn a 20-point similarity gap, no more

_model = None  # (onnxruntime session, tokenizer) while on


def on():
    return _model is not None


def warn(reason):
    global _model
    _model = None
    print(f"warning: the reranker is off: {reason}", file=sys.stderr, flush=True)
    log.event("reranker_off", level=logging.WARNING, reason=reason)


def load():
    """Load the model when RERANKER_ENABLED is on (RERANKER_PATH, RERANKER_THREADS)."""
    global _model
    if os.environ.get("RERANKER_ENABLED", "").strip().lower() not in ("1", "true", "yes", "on"):
        return
    path = os.environ.get("RERANKER_PATH", "").strip() or DEFAULT_PATH
    tokenizer_path = os.path.join(os.path.dirname(path), "tokenizer.json")
    if not (os.path.exists(path) and os.path.exists(tokenizer_path)):
        return warn(f"no model.onnx and tokenizer.json at {os.path.dirname(path)}")
    try:
        import onnxruntime
        from tokenizers import Tokenizer

        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = int(os.environ.get("RERANKER_THREADS", "").strip() or 4)
        session = onnxruntime.InferenceSession(path, options, providers=["CPUExecutionProvider"])
        tokenizer = Tokenizer.from_file(tokenizer_path)
    except Exception as e:  # not installed (uv sync --group rerank), or a broken file
        return warn(f"{type(e).__name__}: {e}")
    tokenizer.enable_truncation(MAX_LENGTH)
    tokenizer.enable_padding(pad_id=tokenizer.token_to_id("[PAD]"), pad_token="[PAD]")
    _model = session, tokenizer


def candidate_text(text):
    """How the model was trained to read a candidate: "हिंदी / latin"."""
    latin = matcher.gloss(text)[0]
    return f"{text} / {latin}" if latin != text else text


def rescore(heard, ranked):
    """ranked (the matcher's order) with the reranker's part added to the top SHORTLIST's score
    and parts, re-sorted. Unchanged when the reranker is off or fails."""
    if _model is None or not ranked:
        return ranked
    session, tokenizer = _model
    short = ranked[:SHORTLIST]
    try:
        encoded = tokenizer.encode_batch([(heard, candidate_text(c["text"])) for c in short])
        feed = {name: np.array([getattr(e, field) for e in encoded], dtype=np.int64) for name, field in
                (("input_ids", "ids"), ("attention_mask", "attention_mask"), ("token_type_ids", "type_ids"))}
        logits = session.run(["logits"], feed)[0].reshape(-1)
    except Exception as e:
        warn(f"{type(e).__name__} while scoring")
        return ranked
    p = np.exp(logits - logits.max())
    weight = float(os.environ.get("RERANKER_WEIGHT", "").strip() or DEFAULT_WEIGHT)
    for c, prob in zip(short, p / p.sum()):
        c["parts"]["rerank"] = round(weight * float(prob), 1)
        c["score"] = round(c["score"] + c["parts"]["rerank"], 1)
    return sorted(short, key=lambda c: c["score"], reverse=True) + ranked[SHORTLIST:]
