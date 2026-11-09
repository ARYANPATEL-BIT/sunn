#!/usr/bin/env python3
"""Safe, controlled smoke-test CLI for Gnani STT and TTS services.

Strictly adheres to Hackathon credit conservation:
1. Performs exactly ONE controlled request per specified service.
2. Uses synthetic, non-sensitive inputs (math sine wave for STT, fixed greeting for TTS).
3. Zero automatic retries to prevent credit loops.
4. Never exposes API keys (masks all headers and responses).
5. Never persists user audio or transcripts to disk.
6. Requires explicit confirmation flag (--confirm-live-credit-spend) to execute.

DO NOT execute against live services without explicit developer authorization.
"""
import argparse
import io
import os
import sys
import time
from pathlib import Path

import numpy as np
import requests
import soundfile
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"


def mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "[NOT SET]"
    return f"{key[:4]}...{key[-4:]}"


def generate_synthetic_audio_wav(seconds: float = 1.0, freq: float = 440.0, rate: int = 16000) -> bytes:
    """Generate a clean synthetic sine tone in memory (no microphone, no sensitive speech)."""
    t = np.arange(int(seconds * rate)) / rate
    waveform = 0.3 * np.sin(2 * np.pi * freq * t)
    buffer = io.BytesIO()
    soundfile.write(buffer, waveform, rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def run_stt_smoke(api_key: str) -> bool:
    print(f"\n[STT Smoke Test] Target: {STT_URL}")
    print(f"[STT Smoke Test] Header: X-API-Key-ID: {mask_key(api_key)}")
    print("[STT Smoke Test] Input: 1.0s synthetic 440 Hz sine tone WAV (in-memory)")
    print("[STT Smoke Test] Request count: exactly 1 request (retries: disabled)")

    audio_bytes = generate_synthetic_audio_wav()
    headers = {"X-API-Key-ID": api_key}
    data = {"language_code": "hi-IN", "format": "verbatim"}
    files = {"audio_file": ("synthetic_tone.wav", audio_bytes, "audio/wav")}

    started = time.monotonic()
    try:
        resp = requests.post(STT_URL, headers=headers, data=data, files=files, timeout=15)
        elapsed = round(1000 * (time.monotonic() - started))
        print(f"[STT Smoke Test] Response: HTTP {resp.status_code} in {elapsed}ms")

        if resp.status_code == 200:
            result = resp.json()
            print(f"[STT Smoke Test] Success: {result.get('success', False)}")
            print(f"[STT Smoke Test] Transcript: '{result.get('transcript', '')}'")
            return True
        else:
            print(f"[STT Smoke Test] Error: HTTP {resp.status_code} - {resp.text[:200]}")
            return False
    except Exception as e:
        elapsed = round(1000 * (time.monotonic() - started))
        print(f"[STT Smoke Test] Network failure after {elapsed}ms: {type(e).__name__} ({e})")
        return False


def run_tts_smoke(api_key: str) -> bool:
    print(f"\n[TTS Smoke Test] Target: {TTS_URL}")
    print(f"[TTS Smoke Test] Header: X-API-Key-ID: {mask_key(api_key)}")
    print("[TTS Smoke Test] Input: 'नमस्ते' (Hindi, voice: Nalini, model: timbre-v2.5)")
    print("[TTS Smoke Test] Request count: exactly 1 request (retries: disabled)")

    headers = {"X-API-Key-ID": api_key}
    body = {
        "text": "नमस्ते",
        "voice": "Nalini",
        "model": "timbre-v2.5",
        "language": "hi-IN",
        "audio_config": {
            "sample_rate": 48000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }

    started = time.monotonic()
    try:
        resp = requests.post(TTS_URL, headers=headers, json=body, timeout=15)
        elapsed = round(1000 * (time.monotonic() - started))
        print(f"[TTS Smoke Test] Response: HTTP {resp.status_code} in {elapsed}ms")

        if resp.status_code == 200:
            content_len = len(resp.content)
            print(f"[TTS Smoke Test] Success: Received {content_len} bytes of audio")
            return True
        else:
            print(f"[TTS Smoke Test] Error: HTTP {resp.status_code} - {resp.text[:200]}")
            return False
    except Exception as e:
        elapsed = round(1000 * (time.monotonic() - started))
        print(f"[TTS Smoke Test] Network failure after {elapsed}ms: {type(e).__name__} ({e})")
        return False


def main():
    parser = argparse.ArgumentParser(description="Controlled live smoke test for Gnani STT and TTS.")
    parser.add_argument("--stt", action="store_true", help="Perform exactly 1 live STT smoke test request")
    parser.add_argument("--tts", action="store_true", help="Perform exactly 1 live TTS smoke test request")
    parser.add_argument("--dry-run", action="store_true", help="Simulate configuration inspection without network calls")
    parser.add_argument(
        "--confirm-live-credit-spend",
        action="store_true",
        help="Mandatory confirmation flag required to execute live requests against Gnani APIs",
    )
    args = parser.parse_args()

    stt_key = os.environ.get("GNANI_STT_API_KEY", "").strip()
    tts_key = os.environ.get("GNANI_TTS_API_KEY", "").strip()

    print("=" * 65)
    print("Sunn Gnani STT/TTS Controlled Smoke-Test Utility")
    print("=" * 65)
    print(f"STT Key Status: {'Configured (' + mask_key(stt_key) + ')' if stt_key and stt_key not in ('your-stt-key-here', 'your-key-here') else 'NOT CONFIGURED / PLACEHOLDER'}")
    print(f"TTS Key Status: {'Configured (' + mask_key(tts_key) + ')' if tts_key and tts_key not in ('your-tts-key-here', 'your-key-here') else 'NOT CONFIGURED / PLACEHOLDER'}")
    print(f"Target Operations: STT={'YES' if args.stt else 'NO'}, TTS={'YES' if args.tts else 'NO'}")
    print("=" * 65)

    if not args.stt and not args.tts:
        print("\nNotice: Neither --stt nor --tts was requested.")
        print("Usage examples:")
        print("  uv run scripts/gnani_live_smoke.py --stt --dry-run")
        print("  uv run scripts/gnani_live_smoke.py --tts --dry-run")
        print("  uv run scripts/gnani_live_smoke.py --stt --confirm-live-credit-spend")
        print("  uv run scripts/gnani_live_smoke.py --tts --confirm-live-credit-spend")
        sys.exit(0)

    if args.dry_run:
        print("\nDry-run mode active. No live network requests will be dispatched.")
        if args.stt:
            print("Plan: Would dispatch exactly 1 STT request to https://api.vachana.ai/stt/v3.")
        if args.tts:
            print("Plan: Would dispatch exactly 1 TTS request to https://api.vachana.ai/api/v1/tts/inference.")
        print("Credit usage: 0 credits consumed.")
        sys.exit(0)

    if not args.confirm_live_credit_spend:
        print("\n[SAFETY STOP] The --confirm-live-credit-spend flag is required to make live calls.")
        print("This safety gate prevents unintended credit consumption during automated runs.")
        print(f"To execute, re-run with: {'--stt ' if args.stt else ''}{'--tts ' if args.tts else ''}--confirm-live-credit-spend")
        sys.exit(1)

    success = True
    if args.stt:
        if not stt_key or stt_key in ("your-stt-key-here", "your-key-here"):
            print("\nError: GNANI_STT_API_KEY is not configured or is set to placeholder.", file=sys.stderr)
            sys.exit(1)
        ok = run_stt_smoke(stt_key)
        success = success and ok

    if args.tts:
        if not tts_key or tts_key in ("your-tts-key-here", "your-key-here"):
            print("\nError: GNANI_TTS_API_KEY is not configured or is set to placeholder.", file=sys.stderr)
            sys.exit(1)
        ok = run_tts_smoke(tts_key)
        success = success and ok

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
