#!/usr/bin/env python3
"""Generate Timbre TTS audio for Sunn Trainings lessons.

Reads content/trainings/audio_manifest.json, checks for existing audio in
web/public/training-audio/<audio_key>.mp3, prints missing files and credit
estimates, and generates missing files up to --max when run with --yes.
Saves word highlighting durations in content/trainings/audio_durations.json.
With GNANI_MOCK=1, writes silent placeholder files for development without credits.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

# Add src to Python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT_DIR, ".env"))

import audio
import gnani
import gnani_mock
import imageio_ffmpeg
import speak

DEFAULT_MANIFEST = os.path.join(ROOT_DIR, "content", "trainings", "audio_manifest.json")
DEFAULT_DURATIONS = os.path.join(ROOT_DIR, "content", "trainings", "audio_durations.json")
DEFAULT_OUT_DIR = os.path.join(ROOT_DIR, "web", "public", "training-audio")


def to_mono_mp3(src_wav_path: str, dst_mp3_path: str):
    """Convert a WAV file to mono 48kbit MP3 using ffmpeg."""
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-loglevel", "error",
            "-i", src_wav_path,
            "-ac", "1",
            "-ar", "24000",
            "-b:a", "48k",
            dst_mp3_path,
        ],
        check=True,
    )


def load_durations(path: str) -> dict[str, float]:
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_durations(path: str, durations: dict[str, float]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(durations, f, ensure_ascii=False, indent=2)


def get_priority(key: str) -> str:
    """Classify training audio key into priority tiers:
    - Priority A (Demo-critical): Core easy-starts-1 and introductions-1 demo phrases (~13 assets).
    - Priority B (Important): Remaining easy-starts, introductions, s-and-sh-1, and sound-play-1 (~53 assets).
    - Priority C (Optional): Advanced tongue twisters and sound play (~62 assets).
    """
    if key.startswith("easy-starts-1-") or key.startswith("introductions-1-greetings-") or key in ("introductions-1-dialogue-1", "introductions-1-dialogue-2"):
        return "A"
    if (
        key.startswith("easy-starts-")
        or key.startswith("introductions-")
        or key.startswith("s-and-sh-1-")
        or key.startswith("sound-play-1-")
    ):
        return "B"
    return "C"


def main():
    parser = argparse.ArgumentParser(description="Generate Timbre TTS audio for trainings lessons.")
    parser.add_argument("--yes", action="store_true", help="Confirm generation of missing audio files")
    parser.add_argument("--dry-run", action="store_true", help="Print estimates and missing counts without generating audio")
    parser.add_argument("--max", type=int, default=250, help="Maximum number of files to generate in this run (default 250)")
    parser.add_argument("--priority", choices=["A", "B", "C", "all"], default="all", help="Target priority tier (A: demo-critical, B: important, C: optional, all)")
    parser.add_argument("--key", help="Target a specific audio key (e.g. easy-starts-1-vowels-aam)")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, help="Path to audio_manifest.json")
    parser.add_argument("--durations", default=DEFAULT_DURATIONS, help="Path to audio_durations.json")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Destination folder for audio files")
    args = parser.parse_args()

    if not os.path.exists(args.manifest):
        print(f"Error: manifest file not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    with open(args.manifest, encoding="utf-8") as f:
        manifest = json.load(f)

    os.makedirs(args.out_dir, exist_ok=True)
    durations = load_durations(args.durations)

    # Check which audio keys are missing
    missing = []
    existing = 0
    total_chars = 0
    priority_counts = {"A": 0, "B": 0, "C": 0}
    priority_missing = {"A": 0, "B": 0, "C": 0}

    for item in manifest:
        key = item["audio_key"]
        text = item["text"]
        p = get_priority(key)
        item["priority"] = p
        priority_counts[p] += 1

        mp3_path = os.path.join(args.out_dir, f"{key}.mp3")
        # Consider present if file exists on disk and duration is recorded
        if os.path.exists(mp3_path) and key in durations and durations[key] > 0:
            existing += 1
        else:
            priority_missing[p] += 1
            if args.key:
                if key == args.key:
                    missing.append(item)
                    total_chars += len(text)
            elif args.priority == "all" or args.priority == p:
                missing.append(item)
                total_chars += len(text)

    missing_count = len(missing)
    estimated_credits = missing_count  # 1 Timbre TTS call per missing file = 1 credit

    print("=" * 60)
    print("Sunn Trainings - Timbre Audio Generator")
    print("=" * 60)
    print(f"Total manifest keys:              {len(manifest)}")
    print(f"  - Priority A (Demo-critical):   {priority_counts['A']} keys ({priority_missing['A']} missing)")
    print(f"  - Priority B (Important):       {priority_counts['B']} keys ({priority_missing['B']} missing)")
    print(f"  - Priority C (Optional):        {priority_counts['C']} keys ({priority_missing['C']} missing)")
    print(f"Target Selection:")
    print(f"  - Priority filter:              {args.priority}")
    if args.key:
        print(f"  - Specific key:                 {args.key}")
    print(f"Existing audio files:             {existing}")
    print(f"Selected missing files to make:   {missing_count}")
    print(f"Total characters to synthesize:   {total_chars}")
    print(f"Estimated Timbre TTS credits:     {estimated_credits} calls")
    print(f"Mock mode (GNANI_MOCK):           {'ON (free synthetic audio)' if gnani_mock.on() else 'OFF (live Gnani API)'}")
    print("=" * 60)

    if args.dry_run:
        print("Dry run complete. No audio generated.")
        sys.exit(0)

    if missing_count == 0:
        print("All audio files are already generated and up to date.")
        sys.exit(0)

    if not args.yes:
        print(f"Stop: {missing_count} audio files need generation.")
        print("Run again with --yes to generate them.")
        sys.exit(1)

    if not gnani_mock.on() and os.environ.get("GNANI_TTS_API_KEY", "").strip() in ("", "your-key-here", "your-tts-key-here"):
        print("Error: GNANI_TTS_API_KEY is not configured in .env (see .env.example).", file=sys.stderr)
        sys.exit(1)

    to_process = missing[:args.max]
    print(f"Generating up to {len(to_process)} audio files (cap: {args.max})...")

    generated_count = 0
    try:
        for idx, item in enumerate(to_process, start=1):
            key = item["audio_key"]
            text = item["text"]
            lang = item.get("lang", "hi")
            mp3_path = os.path.join(args.out_dir, f"{key}.mp3")

            print(f"[{idx}/{len(to_process)}] Synthesizing '{key}' ({lang}, {len(text)} chars)...")

            try:
                # speak.synthesize returns path to a WAV file
                wav_path = speak.synthesize(text, language=lang)
                to_mono_mp3(wav_path, mp3_path)
                dur = audio.seconds(wav_path) or 0.5
                durations[key] = round(dur, 3)
                save_durations(args.durations, durations)
                generated_count += 1
            except gnani.GnaniError as ge:
                print(f"\nStopped on Gnani quota/auth error: {ge.code} - {ge.detail}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"\nStopped on error while generating '{key}': {type(e).__name__} - {e}", file=sys.stderr)
                sys.exit(1)

    finally:
        save_durations(args.durations, durations)

    print(f"\nSuccessfully generated {generated_count} audio files.")
    print(f"Durations saved to {args.durations}.")


if __name__ == "__main__":
    main()
