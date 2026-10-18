import os
import re
import shutil
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import requests
from fastapi import Body, Cookie, Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

import auth
import db
import matcher
import prisma
import speak

DEFAULT_PHRASES = "data/default_phrases_{language}.txt"
USERS_DIR = "data/users"
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

# No CORS: the browser only talks to the Vite dev server, which proxies /api here, so the
# session cookie stays on one https origin.
db.init()
app = FastAPI()


# Prisma/Timbre failures (network, HTTP error, unsuccessful response) come back as 502 with
# source "gnani", so the app can tell them apart from its own server being unreachable.
@app.exception_handler(requests.RequestException)
@app.exception_handler(RuntimeError)
def gnani_failed(request, exc):
    return JSONResponse({"detail": str(exc), "source": "gnani"}, status_code=502)


class Refused(Exception):
    """A request refused for a reason the user can act on; code lets the frontend word it."""

    def __init__(self, status, code, detail, **extra):
        self.status, self.body = status, {"detail": detail, "code": code, **extra}


@app.exception_handler(Refused)
def refused(request, exc):
    return JSONResponse(exc.body, status_code=exc.status)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def public(user):
    return {key: user[key] for key in ("id", "name", "email", "language", "consent_given_at")}


def current_user(sunn_session: str | None = Cookie(None)):
    """The signed-in user from the session cookie. Every per-user route depends on this, so
    nobody can reach another person's data by changing an id."""
    user_id = auth.user_id_from_token(sunn_session) if sunn_session else None
    user = db.row("SELECT * FROM users WHERE id = ?", (user_id,)) if user_id else None
    if user is None:
        raise Refused(401, "no_session", "not signed in")
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


def save_and_transcribe(user, upload):
    """Store the upload as data/users/<id>/<uuid>.wav in Prisma's format; returns (path, hypothesis)."""
    folder = f"{USERS_DIR}/{user['id']}"
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
    return wav, prisma.transcribe(wav, user["language"])


@app.post("/auth/signup")
def signup(response: Response, name: str = Body(), email: str = Body(), password: str = Body(),
           language: Literal["hi", "en"] = Body(), consent: Any = Body(None)):
    name, email = name.strip(), email.strip().lower()
    if consent is not True:
        raise Refused(400, "no_consent", "consent must be true")
    if not name:
        raise Refused(400, "no_name", "name is empty")
    if not EMAIL.fullmatch(email):
        raise Refused(400, "bad_email", "email is not valid")
    if len(password) < auth.MIN_PASSWORD:
        raise Refused(400, "short_password", f"password needs at least {auth.MIN_PASSWORD} characters")
    try:
        user_id = db.execute(
            "INSERT INTO users (name, email, password_hash, language, consent_given_at) VALUES (?, ?, ?, ?, ?)",
            (name, email, auth.hash_password(password), language, now()))
    except sqlite3.IntegrityError:
        raise Refused(409, "email_taken", "an account with this email already exists")
    auth.set_session(response, user_id)
    return public(db.row("SELECT * FROM users WHERE id = ?", (user_id,)))


@app.post("/auth/login")
def login(response: Response, email: str = Body(), password: str = Body()):
    email = email.strip().lower()
    wait = auth.seconds_locked(email)
    if wait:
        raise Refused(429, "too_many_attempts", "too many failed attempts, try again later", retry_after=wait)
    user = db.row("SELECT * FROM users WHERE email = ?", (email,))
    # One message for an unknown email and a wrong password, so neither gives away which.
    if not auth.check_password(user and user["password_hash"], password):
        auth.record_failure(email)
        raise Refused(401, "bad_login", "wrong email or password")
    auth.clear_failures(email)
    auth.set_session(response, user["id"])
    return public(user)


@app.post("/auth/logout")
def logout(response: Response):
    auth.clear_session(response)
    return {"ok": True}


@app.get("/auth/me")
def me(user=Depends(current_user)):
    return public(user)


@app.delete("/me")
def delete_me(response: Response, user=Depends(current_user)):
    """Delete the account, its phrases and recordings, and their cached Prisma transcripts.
    Timbre's cache is left alone: it holds spoken phrase text, shared by everyone who says it."""
    for sample in db.rows("SELECT audio_path FROM samples WHERE user_id = ?", (user["id"],)):
        if os.path.exists(sample["audio_path"]):
            with open(sample["audio_path"], "rb") as f:
                cached = prisma.cache_path(f.read(), user["language"])
            if os.path.exists(cached):
                os.remove(cached)
    db.delete_user(user["id"])
    shutil.rmtree(f"{USERS_DIR}/{user['id']}", ignore_errors=True)
    auth.clear_session(response)
    return {"ok": True}


@app.get("/me/phrases")
def list_phrases(user=Depends(current_user)):
    """Every phrase with its number of enrollment recordings, so enrollment can resume."""
    return db.rows("SELECT p.id, p.text, COUNT(s.id) AS enrolled FROM phrases p"
                   " LEFT JOIN samples s ON s.phrase_id = p.id AND s.source = 'enroll'"
                   " WHERE p.user_id = ? GROUP BY p.id ORDER BY p.id", (user["id"],))


@app.post("/me/phrases")
def add_phrase(text: str = Body(embed=True), user=Depends(current_user)):
    return get_phrase(user["id"], find_or_add_phrase(user["id"], text))


@app.post("/me/phrases/default")
def add_default_phrases(user=Depends(current_user)):
    """Add the everyday phrases in the user's language (data/default_phrases_<hi|en>.txt)."""
    with open(DEFAULT_PHRASES.format(language=user["language"]), encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                find_or_add_phrase(user["id"], line)
    return list_phrases(user)


@app.post("/me/enroll")
def enroll(phrase_id: int = Form(), audio: UploadFile = File(), user=Depends(current_user)):
    get_phrase(user["id"], phrase_id)
    path, hypothesis = save_and_transcribe(user, audio)
    sample_id = db.execute(
        "INSERT INTO samples (user_id, phrase_id, audio_path, prisma_hypothesis, source, created_at)"
        " VALUES (?, ?, ?, ?, 'enroll', ?)", (user["id"], phrase_id, path, hypothesis, now()))
    return {"sample_id": sample_id, "phrase_id": phrase_id, "hypothesis": hypothesis}


@app.post("/me/recognize")
def recognize(audio: UploadFile = File(), user=Depends(current_user)):
    path, hypothesis = save_and_transcribe(user, audio)

    # The bank: every labelled sample, from enrollment and from confirmed corrections.
    bank = db.rows("SELECT phrase_id AS phrase, prisma_hypothesis FROM samples"
                   " WHERE user_id = ? AND phrase_id IS NOT NULL", (user["id"],))
    texts = {p["id"]: p["text"] for p in list_phrases(user)}
    candidates = [{"phrase_id": phrase_id, "text": texts[phrase_id], "score": round(score, 1)}
                  for phrase_id, score in matcher.recognize(hypothesis, bank)]
    top1 = candidates[0]["phrase_id"] if candidates else None

    sample_id = db.execute(
        "INSERT INTO samples (user_id, audio_path, prisma_hypothesis, top1_phrase_id, created_at)"
        " VALUES (?, ?, ?, ?, ?)", (user["id"], path, hypothesis, top1, now()))
    return {
        "sample_id": sample_id,
        "hypothesis": hypothesis,
        "candidates": candidates,
        "low_confidence": not candidates or candidates[0]["score"] < matcher.LOW_CONFIDENCE,
    }


@app.post("/me/confirm")
def confirm(sample_id: int = Body(), phrase_id: int | None = Body(None), new_text: str | None = Body(None),
            user=Depends(current_user)):
    user_id = user["id"]
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
def speak_text(text: str = Body(embed=True), user=Depends(current_user)):
    if not text.strip():
        raise HTTPException(400, "text is empty")
    return FileResponse(speak.synthesize(text.strip(), user["language"]), media_type="audio/wav")


@app.get("/me/stats")
def stats(user=Depends(current_user)):
    counts = db.row("""
        SELECT
            (SELECT COUNT(*) FROM phrases WHERE user_id = :u) AS phrases,
            COUNT(*) FILTER (WHERE source = 'enroll') AS enroll_samples,
            COUNT(*) FILTER (WHERE source IS NOT 'enroll') AS recognitions,
            COUNT(*) FILTER (WHERE source = 'correction') AS confirmed,
            COUNT(*) FILTER (WHERE source = 'correction' AND phrase_id = top1_phrase_id) AS top1_hits
        FROM samples WHERE user_id = :u""", {"u": user["id"]})
    confirmed = counts["confirmed"]
    counts["top1_hit_rate"] = round(counts["top1_hits"] / confirmed, 3) if confirmed else None
    return counts
