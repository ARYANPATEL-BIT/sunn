import argparse
import hashlib
import os
import shutil

import requests
from dotenv import load_dotenv

# From https://docs.gnani.ai/api/TTS/tts-inference.md
URL = "https://api.vachana.ai/api/v1/tts/inference"
# A user's language ("hi" or "en") -> (Timbre language, voice). The docs list no default voice;
# Nalini is their Hindi example and Kaveri their English one, both timbre-v2.5.
VOICES = {"hi": ("hi-IN", "Nalini"), "en": ("en-IN", "Kaveri")}
CACHE_DIR = "data/cache/tts"
OUT = "results/tts_test.wav"


def synthesize(text, language="hi"):
    """Return the path of a cached wav for text; calls Gnani only on a cache miss. The cache
    key covers the whole request body, language and voice included."""
    code, voice = VOICES[language]
    body = {
        "text": text,
        "voice": voice,
        "model": "timbre-v2.5",
        "language": code,
        "audio_config": {"sample_rate": 48000, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "wav"},
    }
    key = hashlib.sha256(repr(sorted(body.items())).encode("utf-8")).hexdigest()
    path = os.path.join(CACHE_DIR, f"{key}.wav")
    if os.path.exists(path):
        print("cache hit, nothing sent")
        return path

    load_dotenv()
    response = requests.post(URL, headers={"X-API-Key-ID": os.environ["GNANI_API_KEY"]}, json=body, timeout=60)
    response.raise_for_status()
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "wb") as f:
        f.write(response.content)
    print("sent 1 request to Gnani TTS")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="नमस्ते, मुझे पानी चाहिए")
    parser.add_argument("--language", choices=sorted(VOICES), default="hi")
    args = parser.parse_args()

    os.makedirs("results", exist_ok=True)
    shutil.copy(synthesize(args.text, args.language), OUT)
    print(f"saved {OUT}")
