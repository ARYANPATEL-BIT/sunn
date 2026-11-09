import argparse
import hashlib
import json
import os
import shutil

import audio
import db
import gnani
import gnani_mock

# From https://docs.gnani.ai/api/TTS/tts-inference.md and https://docs.gnani.ai/api/VC/vc-inference.md:
# a stock voice and a cloned voice go to the same endpoint, with different bodies.
URL = "https://api.vachana.ai/api/v1/tts/inference"
# From https://docs.gnani.ai/api/VC/voice-clone-embeddings.md
CLONE_URL = "https://api.vachana.ai/api/v1/tts/voice-clone/embeddings"
# A phrase's language -> its stock voice, one whose preferred language it is in
# docs.gnani.ai/api/TTS/available-voices.md (Timbre v2.5). Nalini and Kaveri are the docs' Hindi
# and English examples; the rest are female voices, like them.
MODEL = os.environ.get("TIMBRE_MODEL", "").strip() or "timbre-v2.5"
VOICES = {"en": "Kaveri", "hi": "Nalini", "ta": "Noopur", "te": "Lavanya", "kn": "Saanvi", "ml": "Reshma",
          "mr": "Zahira", "gu": "Falak", "bn": "Kirra", "pa": "Mehuli"}
# The docs give no language list for voice cloning (vachana-vc-v1 takes no language); every
# example they give is Hindi, so only Hindi offers the user's own voice.
CLONE_LANGUAGES = {"hi"}
CACHE_DIR = os.path.join(db.DATA_DIR, "cache", "tts")
OUT = "results/tts_test.wav"


def request_body(text, language, embedding=None):
    """The stock voice for the language, or the cloned voice when embedding is given. The VC
    request takes no language or voice, and its sample_rate tops out at 44100."""
    if not text or not text.strip():
        raise ValueError("text to synthesize cannot be empty")
    if embedding is not None:
        return {"text": text, "model": "vachana-vc-v1", "speaker_embedding": embedding,
                "audio_config": {"sample_rate": 44100, "num_channels": 1, "sample_width": 2,
                                 "encoding": "linear_pcm", "container": "wav"}}
    if language not in VOICES:
        raise ValueError(f"unsupported language '{language}'; supported languages are {sorted(VOICES)}")
    return {
        "text": text,
        "voice": VOICES[language],
        "model": MODEL,
        "language": f"{language}-IN",
        "audio_config": {"sample_rate": 48000, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "wav"},
    }


def synthesize(text, language="hi", embedding=None, cache_dir=CACHE_DIR, user_id=None):
    """Return the path of a cached wav for text; calls Gnani only on a cache miss. The cache
    key covers the whole request body, so the language and the voice (stock or cloned) are
    part of it. user_id is who the call is for (see gnani.post)."""
    body = request_body(text, language, embedding)
    if gnani_mock.on():
        return gnani_mock.silence()
    key = hashlib.sha256(repr(sorted(body.items())).encode("utf-8")).hexdigest()
    path = os.path.join(cache_dir, f"{key}.wav")
    if os.path.exists(path):
        gnani.record("tts", True, audio.seconds(path), user_id)
        return path

    response = gnani.post("tts", URL, user_id=user_id, json=body)
    if not response.content or len(response.content) < 44 or audio.seconds(response.content) is None:
        raise gnani.GnaniError("gnani_rejected", "Gnani returned an empty or invalid audio response")
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "wb") as f:
        f.write(response.content)
    return path


def clone_voice(wav_path, cache_dir, user_id=None):
    """Gnani's speaker_embedding ({embedding, shape, dtype}) for a reference recording; calls
    Gnani only on a cache miss. The cache holds a voiceprint, so it lives in cache_dir, inside
    the user's own folder, and goes when they remove their voice."""
    if gnani_mock.on():
        return dict(gnani_mock.EMBEDDING)
    with open(wav_path, "rb") as f:
        audio_bytes = f.read()
    seconds = audio.seconds(audio_bytes)
    path = os.path.join(cache_dir, f"{hashlib.sha256(audio_bytes).hexdigest()}.json")
    if os.path.exists(path):
        gnani.record("clone", True, seconds, user_id)
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    response = gnani.post("clone", CLONE_URL, audio_seconds=seconds, user_id=user_id,
                          files={"audio_file": ("voice.wav", audio_bytes, "audio/wav")})
    try:
        result = response.json()
    except Exception:
        raise gnani.GnaniError("gnani_rejected", "Gnani voice clone returned a malformed response")
    # The endpoint's schema nests it under data.voice_clone_embedding; the quick start shows
    # it at the top level. Accept either.
    found = (result.get("data") or {}).get("voice_clone_embedding") or result
    if result.get("success") is False or not all(found.get(k) for k in ("embedding", "shape", "dtype")):
        raise gnani.GnaniError("gnani_rejected", "Gnani returned no voice embedding")
    embedding = {k: found[k] for k in ("embedding", "shape", "dtype")}
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(embedding, f)
    return embedding


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="नमस्ते, मुझे पानी चाहिए")
    parser.add_argument("--language", choices=sorted(VOICES), default="hi")
    args = parser.parse_args()

    db.init()  # api_calls lives there
    os.makedirs("results", exist_ok=True)
    shutil.copy(synthesize(args.text, args.language), OUT)
    print(f"saved {OUT}")
