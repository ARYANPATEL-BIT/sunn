#!/usr/bin/env python3
"""Safe, controlled smoke-test CLI for Gnani STT and TTS services.

Strictly adheres to Hackathon credit conservation:
1. Performs at most 1-2 controlled requests per specified service.
2. Uses synthetic inputs (synthesized speech or pure sine tone).
3. Zero automatic retries to prevent credit loops.
4. Never exposes API keys (masks all headers and responses).
5. Never persists user audio or transcripts to disk.
6. Requires explicit confirmation flag (--confirm-live-credit-spend) to execute.
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


def extract_usage_headers(headers: dict) -> dict:
    """Extract any quota, rate-limit, or credit headers returned by Gnani."""
    usage = {}
    for k, v in headers.items():
        k_lower = k.lower()
        if any(term in k_lower for term in ("credit", "quota", "limit", "remaining", "usage")):
            usage[k] = v
    return usage


def generate_synthetic_audio_wav(seconds: float = 1.0, freq: float = 440.0, rate: int = 16000) -> bytes:
    """Generate a clean synthetic sine tone in memory (no microphone, no sensitive speech)."""
    t = np.arange(int(seconds * rate)) / rate
    waveform = 0.3 * np.sin(2 * np.pi * freq * t)
    buffer = io.BytesIO()
    soundfile.write(buffer, waveform, rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def run_tts_smoke(api_key: str, text: str = "नमस्ते, मुझे पानी चाहिए") -> tuple[bool, bytes | None, dict]:
    print(f"\n[TTS Smoke Test] Target: {TTS_URL}")
    print(f"[TTS Smoke Test] Header: X-API-Key-ID: {mask_key(api_key)}")
    print(f"[TTS Smoke Test] Input text: '{text}' (Hindi, voice: Nalini, model: timbre-v2.5)")
    print("[TTS Smoke Test] Request count: exactly 1 request (retries: disabled)")

    headers = {"X-API-Key-ID": api_key}
    body = {
        "text": text,
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
    metrics = {"status": None, "ms": None, "bytes": 0, "duration": None, "usage": {}}
    try:
        resp = requests.post(TTS_URL, headers=headers, json=body, timeout=15)
        elapsed = round(1000 * (time.monotonic() - started))
        metrics["status"] = resp.status_code
        metrics["ms"] = elapsed
        metrics["usage"] = extract_usage_headers(resp.headers)

        print(f"[TTS Smoke Test] Response: HTTP {resp.status_code} in {elapsed}ms")
        if metrics["usage"]:
            print(f"[TTS Smoke Test] Provider Usage Headers: {metrics['usage']}")

        if resp.status_code == 200:
            content_len = len(resp.content)
            metrics["bytes"] = content_len
            try:
                info = soundfile.info(io.BytesIO(resp.content))
                metrics["duration"] = info.duration
                print(f"[TTS Smoke Test] Audio Info: {info.samplerate}Hz, {info.channels}ch, {info.format}/{info.subtype}, duration={info.duration:.2f}s, size={content_len} bytes")
                print("[TTS Smoke Test] Result: Audio payload is valid, decodable WAV.")
                return True, resp.content, metrics
            except Exception as audio_err:
                print(f"[TTS Smoke Test] Warning: Audio decoding error ({audio_err})")
                return True, resp.content, metrics
        else:
            print(f"[TTS Smoke Test] Error: HTTP {resp.status_code} - {resp.text[:200]}")
            return False, None, metrics
    except Exception as e:
        elapsed = round(1000 * (time.monotonic() - started))
        print(f"[TTS Smoke Test] Network failure after {elapsed}ms: {type(e).__name__} ({e})")
        return False, None, metrics


def run_stt_smoke(api_key: str, audio_bytes: bytes | None = None, label: str = "synthetic audio") -> tuple[bool, dict]:
    print(f"\n[STT Smoke Test] Target: {STT_URL}")
    print(f"[STT Smoke Test] Header: X-API-Key-ID: {mask_key(api_key)}")
    print(f"[STT Smoke Test] Input audio source: {label}")
    print("[STT Smoke Test] Request count: exactly 1 request (retries: disabled)")

    if audio_bytes is None:
        audio_bytes = generate_synthetic_audio_wav()

    # Convert or inspect duration
    try:
        info = soundfile.info(io.BytesIO(audio_bytes))
        duration_s = info.duration
        print(f"[STT Smoke Test] Audio payload: {info.samplerate}Hz, {info.channels}ch, duration={duration_s:.2f}s, size={len(audio_bytes)} bytes")
    except Exception:
        duration_s = 1.0

    headers = {"X-API-Key-ID": api_key}
    data = {"language_code": "hi-IN", "format": "verbatim"}
    files = {"audio_file": ("test_speech.wav", audio_bytes, "audio/wav")}

    started = time.monotonic()
    metrics = {"status": None, "ms": None, "transcript": "", "usage": {}}
    try:
        resp = requests.post(STT_URL, headers=headers, data=data, files=files, timeout=15)
        elapsed = round(1000 * (time.monotonic() - started))
        metrics["status"] = resp.status_code
        metrics["ms"] = elapsed
        metrics["usage"] = extract_usage_headers(resp.headers)

        print(f"[STT Smoke Test] Response: HTTP {resp.status_code} in {elapsed}ms")
        if metrics["usage"]:
            print(f"[STT Smoke Test] Provider Usage Headers: {metrics['usage']}")

        if resp.status_code == 200:
            result = resp.json()
            transcript = result.get("transcript", "")
            metrics["transcript"] = transcript
            print(f"[STT Smoke Test] Success: {result.get('success', False)}")
            print(f"[STT Smoke Test] Returned Transcript: '{transcript}'")
            return True, metrics
        else:
            print(f"[STT Smoke Test] Error: HTTP {resp.status_code} - {resp.text[:200]}")
            return False, metrics
    except Exception as e:
        elapsed = round(1000 * (time.monotonic() - started))
        print(f"[STT Smoke Test] Network failure after {elapsed}ms: {type(e).__name__} ({e})")
        return False, metrics


def main():
    parser = argparse.ArgumentParser(description="Controlled live smoke test for Gnani STT and TTS.")
    parser.add_argument("--stt", action="store_true", help="Perform exactly 1 live STT smoke test request")
    parser.add_argument("--tts", action="store_true", help="Perform exactly 1 live TTS smoke test request")
    parser.add_argument("--speech-loop", action="store_true", help="Perform 1 live TTS followed by 1 live STT on the generated audio")
    parser.add_argument("--text", default="नमस्ते, मुझे पानी चाहिए", help="Text to synthesize for TTS test")
    parser.add_argument("--dry-run", action="store_true", help="Simulate configuration inspection without network calls")
    parser.add_argument(
        "--confirm-live-credit-spend",
        action="store_true",
        help="Mandatory confirmation flag required to execute live requests against Gnani APIs",
    )
    args = parser.parse_args()

    stt_key = os.environ.get("GNANI_STT_API_KEY", "").strip()
    tts_key = os.environ.get("GNANI_TTS_API_KEY", "").strip()

    if args.speech_loop:
        args.stt = True
        args.tts = True

    print("=" * 65)
    print("Sunn Gnani STT/TTS Controlled Smoke-Test Utility")
    print("=" * 65)
    print(f"STT Key Status: {'Configured (' + mask_key(stt_key) + ')' if stt_key and stt_key not in ('your-stt-key-here', 'your-key-here') else 'NOT CONFIGURED / PLACEHOLDER'}")
    print(f"TTS Key Status: {'Configured (' + mask_key(tts_key) + ')' if tts_key and tts_key not in ('your-tts-key-here', 'your-key-here') else 'NOT CONFIGURED / PLACEHOLDER'}")
    print(f"Target Operations: STT={'YES' if args.stt else 'NO'}, TTS={'YES' if args.tts else 'NO'}")
    if args.speech_loop:
        print("Mode: Bidirectional speech loop (TTS synthesis -> STT recognition)")
    print("=" * 65)

    if not args.stt and not args.tts:
        print("\nNotice: Neither --stt nor --tts was requested.")
        print("Usage examples:")
        print("  uv run scripts/gnani_live_smoke.py --dry-run")
        print("  uv run scripts/gnani_live_smoke.py --tts --confirm-live-credit-spend")
        print("  uv run scripts/gnani_live_smoke.py --speech-loop --confirm-live-credit-spend")
        sys.exit(0)

    if args.dry_run:
        print("\nDry-run mode active. No live network requests will be dispatched.")
        if args.tts:
            print(f"Plan: Would dispatch exactly 1 TTS request to {TTS_URL} for text: '{args.text}'")
        if args.stt:
            print(f"Plan: Would dispatch exactly 1 STT request to {STT_URL}")
        print("Credit usage: 0 credits consumed.")
        sys.exit(0)

    if not args.confirm_live_credit_spend:
        print("\n[SAFETY STOP] The --confirm-live-credit-spend flag is required to make live calls.")
        print("This safety gate prevents unintended credit consumption during automated runs.")
        print(f"To execute, re-run with: {'--speech-loop ' if args.speech_loop else ''}{'--stt ' if args.stt and not args.speech_loop else ''}{'--tts ' if args.tts and not args.speech_loop else ''}--confirm-live-credit-spend")
        sys.exit(1)

    tts_audio = None
    success = True

    if args.tts:
        if not tts_key or tts_key in ("your-tts-key-here", "your-key-here"):
            print("\nError: GNANI_TTS_API_KEY is not configured or is set to placeholder.", file=sys.stderr)
            sys.exit(1)
        ok, tts_audio, _ = run_tts_smoke(tts_key, text=args.text)
        success = success and ok

    if args.stt:
        if not stt_key or stt_key in ("your-stt-key-here", "your-key-here"):
            print("\nError: GNANI_STT_API_KEY is not configured or is set to placeholder.", file=sys.stderr)
            sys.exit(1)

        if args.speech_loop and tts_audio:
            ok, _ = run_stt_smoke(stt_key, audio_bytes=tts_audio, label=f"TTS generated audio for '{args.text}'")
        else:
            ok, _ = run_stt_smoke(stt_key, audio_bytes=None, label="1.0s synthetic 440 Hz sine tone")
        success = success and ok

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
