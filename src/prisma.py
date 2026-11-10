import hashlib
import json
import os

import audio
import db
import gnani
import gnani_mock
import languages

# From https://docs.gnani.ai/api/STT/speech-to-text.md. No model field: Prisma v2.5, the default,
# takes all ten languages (docs.gnani.ai/api/STT/models/prisma-v2-5.md).
URL = "https://api.vachana.ai/stt/v3"
# A user's language -> Prisma language_code. en-IN is Indian English, and takes Hinglish too.
LANGUAGES = {code: f"{code}-IN" for code in languages.CODES}
CACHE_DIR = os.path.join(db.DATA_DIR, "cache", "prisma")


def request_form(language):
    return {"language_code": LANGUAGES[language], "format": "verbatim"}


def cache_path(audio_bytes, language):
    """Where the transcript of these wav bytes is cached. The language code is part of the
    request, so it is part of the key too."""
    key = hashlib.sha256(audio_bytes + repr(sorted(request_form(language).items())).encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.json")


def transcribe(wav_path, language="hi", user_id=None, quota="stt"):
    """Prisma transcript for a wav; calls Gnani only on a cache miss. user_id is who the call is
    for, and quota the daily limit it counts against: stt, or enroll (see gnani.post)."""
    with open(wav_path, "rb") as f:
        audio_bytes = f.read()
    if gnani_mock.on():
        return gnani_mock.transcript(audio_bytes, language)
    seconds = audio.seconds(audio_bytes)
    path = cache_path(audio_bytes, language)
    if os.path.exists(path):
        gnani.record_cached("stt", seconds, user_id)
        with open(path, encoding="utf-8") as f:
            return json.load(f)["transcript"]

    response = gnani.post("stt", URL, audio_seconds=seconds, user_id=user_id, quota=quota, data=request_form(language),
                          files={"audio_file": ("audio.wav", audio_bytes, "audio/wav")})
    try:
        result = response.json()
    except Exception:
        raise gnani.GnaniError("gnani_rejected", "Prisma returned a malformed response")
    if not isinstance(result, dict) or not result.get("success"):
        raise gnani.GnaniError("gnani_rejected", "Prisma could not transcribe the audio")
    transcript = result.get("transcript")
    if transcript is None:
        raise gnani.GnaniError("gnani_rejected", "Prisma response is missing the transcript field")
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return transcript
