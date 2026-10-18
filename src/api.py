import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import db
import matcher
import prisma
import speak

DEFAULT_PHRASES = "data/default_phrases_hi.txt"
USERS_DIR = "data/users"
# The Vite dev server (port 5173) on this machine or on a private LAN address, so a
# phone on the same Wi-Fi can call the API. https too, since phones only allow the
# microphone on secure pages.
CORS_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1|10(\.\d+){3}|192\.168(\.\d+){2}|172\.(1[6-9]|2\d|3[01])(\.\d+){2}):5173"

db.init()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origin_regex=CORS_ORIGIN_REGEX, allow_methods=["*"], allow_headers=["*"])


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_user(user_id):
    user = db.row("SELECT * FROM users WHERE id = ?", (user_id,))
    if user is None:
        raise HTTPException(404, "user not found")
    return user


def get_phrase(user_id, phrase_id):
    phrase = db.row("SELECT id, text FROM phrases WHERE id = ? AND user_id = ?", (phrase_id, user_id))
    if phrase is None:
        raise HTTPException(404, "phrase not found")
    return phrase


def find_or_add_phrase(user_id, text):
    """Phrase id for text, reusing an identical phrase so one phrase never splits the bank."""
    text = text.strip()
    if not text:
        raise HTTPException(400, "text is empty")
    phrase = db.row("SELECT id FROM phrases WHERE user_id = ? AND text = ?", (user_id, text))
    if phrase:
        return phrase["id"]
    return db.execute("INSERT INTO phrases (user_id, text) VALUES (?, ?)", (user_id, text))


def save_and_transcribe(user_id, upload):
    """Store the upload as data/users/<id>/<uuid>.wav in Prisma's format; returns (path, hypothesis)."""
    folder = f"{USERS_DIR}/{user_id}"
    name = uuid.uuid4().hex
    raw, wav = f"{folder}/{name}.upload", f"{folder}/{name}.wav"
    os.makedirs(folder, exist_ok=True)
    with open(raw, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    try:
        prisma.to_wav(raw, wav)
    except subprocess.CalledProcessError:
        raise HTTPException(400, "could not read the audio file")
    finally:
        os.remove(raw)
    return wav, prisma.transcribe(wav)


@app.post("/users")
def create_user(name: str = Body(), language: str = Body(), consent: Any = Body(None)):
    if consent is not True:
        raise HTTPException(400, "consent must be true")
    user_id = db.execute("INSERT INTO users (name, language, consent_given_at) VALUES (?, ?, ?)",
                         (name, language, now()))
    return get_user(user_id)


@app.get("/users/{user_id}/phrases")
def list_phrases(user_id: int):
    get_user(user_id)
    return db.rows("SELECT id, text FROM phrases WHERE user_id = ? ORDER BY id", (user_id,))


@app.post("/users/{user_id}/phrases")
def add_phrase(user_id: int, text: str = Body(embed=True)):
    get_user(user_id)
    return get_phrase(user_id, find_or_add_phrase(user_id, text))


@app.post("/users/{user_id}/phrases/default")
def add_default_phrases(user_id: int):
    get_user(user_id)
    with open(DEFAULT_PHRASES, encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                find_or_add_phrase(user_id, line)
    return list_phrases(user_id)


@app.post("/users/{user_id}/enroll")
def enroll(user_id: int, phrase_id: int = Form(), audio: UploadFile = File()):
    get_user(user_id)
    get_phrase(user_id, phrase_id)
    path, hypothesis = save_and_transcribe(user_id, audio)
    sample_id = db.execute(
        "INSERT INTO samples (user_id, phrase_id, audio_path, prisma_hypothesis, source, created_at)"
        " VALUES (?, ?, ?, ?, 'enroll', ?)", (user_id, phrase_id, path, hypothesis, now()))
    return {"sample_id": sample_id, "phrase_id": phrase_id, "hypothesis": hypothesis}


@app.post("/users/{user_id}/recognize")
def recognize(user_id: int, audio: UploadFile = File()):
    get_user(user_id)
    path, hypothesis = save_and_transcribe(user_id, audio)

    # The bank: every labelled sample, from enrollment and from confirmed corrections.
    bank = db.rows("SELECT phrase_id AS phrase, prisma_hypothesis FROM samples"
                   " WHERE user_id = ? AND phrase_id IS NOT NULL", (user_id,))
    texts = {p["id"]: p["text"] for p in list_phrases(user_id)}
    candidates = [{"phrase_id": phrase_id, "text": texts[phrase_id], "score": round(score, 1)}
                  for phrase_id, score in matcher.recognize(hypothesis, bank)]
    top1 = candidates[0]["phrase_id"] if candidates else None

    sample_id = db.execute(
        "INSERT INTO samples (user_id, audio_path, prisma_hypothesis, top1_phrase_id, created_at)"
        " VALUES (?, ?, ?, ?, ?)", (user_id, path, hypothesis, top1, now()))
    return {
        "sample_id": sample_id,
        "hypothesis": hypothesis,
        "candidates": candidates,
        "low_confidence": not candidates or candidates[0]["score"] < matcher.LOW_CONFIDENCE,
    }


@app.post("/users/{user_id}/confirm")
def confirm(user_id: int, sample_id: int = Body(), phrase_id: int | None = Body(None),
            new_text: str | None = Body(None)):
    get_user(user_id)
    if (phrase_id is None) == (new_text is None):
        raise HTTPException(400, "send exactly one of phrase_id or new_text")
    sample = db.row("SELECT id FROM samples WHERE id = ? AND user_id = ? AND source IS NOT 'enroll'",
                    (sample_id, user_id))
    if sample is None:
        raise HTTPException(404, "recognition sample not found")

    phrase = get_phrase(user_id, find_or_add_phrase(user_id, new_text) if new_text is not None else phrase_id)
    db.execute("UPDATE samples SET phrase_id = ?, source = 'correction' WHERE id = ?", (phrase["id"], sample_id))
    return {"sample_id": sample_id, "phrase_id": phrase["id"], "text": phrase["text"]}


@app.post("/speak")
def speak_text(text: str = Body(embed=True)):
    if not text.strip():
        raise HTTPException(400, "text is empty")
    return FileResponse(speak.synthesize(text.strip()), media_type="audio/wav")


@app.get("/users/{user_id}/stats")
def stats(user_id: int):
    get_user(user_id)
    counts = db.row("""
        SELECT
            (SELECT COUNT(*) FROM phrases WHERE user_id = :u) AS phrases,
            COUNT(*) FILTER (WHERE source = 'enroll') AS enroll_samples,
            COUNT(*) FILTER (WHERE source IS NOT 'enroll') AS recognitions,
            COUNT(*) FILTER (WHERE source = 'correction') AS confirmed,
            COUNT(*) FILTER (WHERE source = 'correction' AND phrase_id = top1_phrase_id) AS top1_hits
        FROM samples WHERE user_id = :u""", {"u": user_id})
    confirmed = counts["confirmed"]
    counts["top1_hit_rate"] = round(counts["top1_hits"] / confirmed, 3) if confirmed else None
    return counts
