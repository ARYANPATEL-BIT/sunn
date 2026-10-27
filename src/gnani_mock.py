"""GNANI_MOCK=1: answer every Gnani call here instead, so testing the app spends no credits.

Prisma's transcript of a recording comes from gnani_mock.json: by the sha256 of the 16 kHz wav
the server stores (data/users/<id>/*.wav), else the default for the user's language. Timbre
answers half a second of silence, and voice cloning a made-up embedding. Nothing is cached or
counted in api_calls, so mock answers never mix with real ones.

Only for local testing: the server refuses to start with both GNANI_MOCK and TRUST_PROXY set,
since TRUST_PROXY means it is deployed behind a proxy."""
import hashlib
import io
import json
import logging
import os
import sys
import wave

import db
import log

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gnani_mock.json")
EMBEDDING = {"embedding": "bW9jaw==", "shape": [1, 768], "dtype": "torch.bfloat16"}


def on():
    return os.environ.get("GNANI_MOCK", "").strip().lower() in ("1", "true", "yes", "on")


def check_startup(behind_proxy):
    """Refuse mock mode behind a proxy (production); otherwise say loudly that it is on."""
    if not on():
        return
    if behind_proxy:
        raise RuntimeError("GNANI_MOCK and TRUST_PROXY are both set: mock mode is for local testing only."
                           " Unset GNANI_MOCK.")
    line = "!" * 78
    print(f"{line}\n!! GNANI_MOCK is on: every Prisma and Timbre answer is FAKE ({FIXTURES}).\n"
          f"!! For local testing only. Unset GNANI_MOCK to use Gnani.\n{line}", file=sys.stderr, flush=True)
    log.event("gnani_mock_on", level=logging.WARNING)


def transcript(audio_bytes, language):
    with open(FIXTURES, encoding="utf-8") as f:
        fixtures = json.load(f)
    return fixtures["by_sha256"].get(hashlib.sha256(audio_bytes).hexdigest(), fixtures["default"][language])


def silence():
    """The path of a 0.5 s silent wav, written once."""
    path = os.path.join(db.DATA_DIR, "mock", "silence.wav")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes(b"\0\0" * 24000)
        with open(path, "wb") as f:
            f.write(buffer.getvalue())
    return path
