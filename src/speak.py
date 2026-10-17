import argparse
import hashlib
import os
import shutil

import requests
from dotenv import load_dotenv

# From https://docs.gnani.ai/api/TTS/tts-inference.md
URL = "https://api.vachana.ai/api/v1/tts/inference"
VOICE = "Nalini"  # docs list no default voice; Nalini is the one used in the docs' hi-IN example
CACHE_DIR = "data/cache/tts"
OUT = "results/tts_test.wav"


def synthesize(text):
    """Return the path of a cached wav for text; calls Gnani only on a cache miss."""
    body = {
        "text": text,
        "voice": VOICE,
        "model": "timbre-v2.5",
        "language": "hi-IN",
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
    args = parser.parse_args()

    os.makedirs("results", exist_ok=True)
    shutil.copy(synthesize(args.text), OUT)
    print(f"saved {OUT}")
