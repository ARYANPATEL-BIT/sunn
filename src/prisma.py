import hashlib
import json
import os

import audio
import gnani

# From https://docs.gnani.ai/api/STT/speech-to-text.md
URL = "https://api.vachana.ai/stt/v3"
# A user's language ("hi" or "en") -> Prisma language_code. en-IN is Indian English.
LANGUAGES = {"hi": "hi-IN", "en": "en-IN"}
CACHE_DIR = "data/cache/prisma"


def request_form(language):
    return {"language_code": LANGUAGES[language], "format": "verbatim"}


def cache_path(audio_bytes, language):
    """Where the transcript of these wav bytes is cached. The language code is part of the
    request, so it is part of the key too."""
    key = hashlib.sha256(audio_bytes + repr(sorted(request_form(language).items())).encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.json")


def transcribe(wav_path, language="hi"):
    """Prisma transcript for a wav; calls Gnani only on a cache miss."""
    with open(wav_path, "rb") as f:
        audio_bytes = f.read()
    seconds = audio.seconds(audio_bytes)
    path = cache_path(audio_bytes, language)
    if os.path.exists(path):
        gnani.record("stt", True, seconds)
        with open(path, encoding="utf-8") as f:
            return json.load(f)["transcript"]

    response = gnani.post("stt", URL, audio_seconds=seconds, data=request_form(language),
                          files={"audio_file": ("audio.wav", audio_bytes, "audio/wav")})
    result = response.json()
    if not result.get("success"):
        raise gnani.GnaniError("gnani_rejected", "Prisma could not transcribe the audio")
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result["transcript"]
