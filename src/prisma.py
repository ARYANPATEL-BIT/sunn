import hashlib
import json
import os
import subprocess

import imageio_ffmpeg
import requests
from dotenv import load_dotenv

# From https://docs.gnani.ai/api/STT/speech-to-text.md
URL = "https://api.vachana.ai/stt/v3"
LANGUAGE = "hi-IN"
CACHE_DIR = "data/cache/prisma"


def to_wav(src_path, dst_path):
    """Convert any upload (webm/ogg/mp4 from MediaRecorder) to 16 kHz mono 16-bit PCM WAV,
    the rate the docs say Prisma resamples to. bitexact keeps ffmpeg's version string
    out of the file, so the same recording always hashes the same."""
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", src_path,
         "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-map_metadata", "-1",
         "-fflags", "+bitexact", "-flags:a", "+bitexact", dst_path],
        check=True,
    )


def transcribe(wav_path):
    """Prisma transcript for a wav; calls Gnani only on a cache miss."""
    form = {"language_code": LANGUAGE, "format": "verbatim"}
    with open(wav_path, "rb") as f:
        audio = f.read()
    key = hashlib.sha256(audio + repr(sorted(form.items())).encode("utf-8")).hexdigest()
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)["transcript"]

    load_dotenv()
    response = requests.post(URL, headers={"X-API-Key-ID": os.environ["GNANI_API_KEY"]},
                             files={"audio_file": ("audio.wav", audio, "audio/wav")}, data=form, timeout=60)
    response.raise_for_status()
    result = response.json()
    if not result.get("success"):
        raise RuntimeError(f"Prisma failed: {result}")
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result["transcript"]
