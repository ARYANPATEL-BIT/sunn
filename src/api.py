import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import time
import traceback
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import requests
from fastapi import Cookie, Depends, FastAPI, File, Form, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException

import audio
import auth
import db
import gnani
import gnani_mock
import languages
import llm_judge
import log
import matcher
import prisma
import reranker
import schemas
import speak

# Part of the code, so read from the repo whatever DATA_DIR is.
DEFAULT_PHRASES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "data", "default_phrases_{language}.txt")
USERS_DIR = os.path.join(db.DATA_DIR, "users")
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PHONE = re.compile(r"[1-9]\d{7,14}")  # E.164: country code first, at most 15 digits

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
PHRASE_SECONDS = (0.3, 15)  # a phrase, slot word or fixed part recording
VOICE_SECONDS = (5, 30)  # reference audio for cloning, from the voice clone embeddings docs

# The group comments in data/default_phrases_*.txt -> contexts for the phrases under them.
GROUP_CONTEXTS = {"help": "any", "basic needs": "home,hospital", "pain and health": "hospital",
                  "food and drink": "home", "family": "home", "greetings and politeness": "any"}
# Urgent by text, or in the other languages' files by meaning (their third column).
URGENT_PHRASES = {"मदद चाहिए", "दर्द हो रहा है", "I need help", "I'm in pain"}
# Building blocks every new user starts with, in Hindi and English only for now.
# बेटे, not बेटा: the only person template takes को.
DEFAULT_SLOT_WORDS = {
    "hi": {"item": ["पानी", "दवाई", "खाना", "चाय", "कंबल"], "person": ["बेटे", "बेटी", "डॉक्टर", "नर्स"]},
    "en": {"item": ["water", "my medicine", "food", "tea", "a blanket"],
           "person": ["my son", "my daughter", "the doctor", "the nurse"]},
}
DEFAULT_TEMPLATES = {"hi": ["{item} चाहिए", "{person} को बुलाओ"], "en": ["I need {item}", "Call {person}"]}

# No CORS: the browser only ever talks to one origin, which serves this API under /api (the Vite
# dev server proxies it here; in production src/server.py mounts it), so the session cookie
# just works.
db.init()
# Every error is schemas.Error, so /docs shows that one shape for any 4xx or 5xx.
app = FastAPI(responses={"4XX": {"model": schemas.Error}, "5XX": {"model": schemas.Error}})


class Refused(Exception):
    """A request refused for a reason the user can act on; code (a schemas.ErrorCode) lets the
    frontend word it, message says it in plain English."""

    def __init__(self, status, code, message, **extra):
        self.status, self.body = status, {"error": code, "message": message, **extra}


@app.exception_handler(Refused)
def refused(request, exc):
    log.event("refused", path=request.url.path, status=exc.status, code=exc.body["error"])
    return JSONResponse(exc.body, status_code=exc.status)


@app.exception_handler(gnani.GnaniError)
def gnani_failed(request, exc):
    log.event("gnani_failed", level=logging.WARNING, path=request.url.path, code=exc.code)
    return JSONResponse({"error": exc.code, "message": exc.detail, **exc.extra}, status_code=exc.status)


@app.exception_handler(RequestValidationError)
def invalid_input(request, exc):
    """A body, form or path value of the wrong shape, like "{field}: {what's wrong}"."""
    error = exc.errors()[0]
    field = ".".join(str(part) for part in error["loc"][1:]) or "body"
    log.event("refused", path=request.url.path, status=422, code="invalid_input")
    return JSONResponse({"error": "invalid_input", "message": f"{field}: {error['msg']}"}, status_code=422)


@app.exception_handler(HTTPException)
def http_error(request, exc):
    """FastAPI's own refusals: an unknown path, or a method the path doesn't take."""
    code = "not_found" if exc.status_code == 404 else "invalid_input"
    return JSONResponse({"error": code, "message": str(exc.detail).lower()}, status_code=exc.status_code,
                        headers=exc.headers)


@app.exception_handler(Exception)
def server_error(request, exc):
    return JSONResponse({"error": "server_error", "message": "something went wrong on the server"},
                        status_code=500)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        log.event("error", level=logging.ERROR, method=request.method, path=request.url.path,
                  traceback=traceback.format_exc())
        raise
    log.event("request", method=request.method, path=request.url.path, status=response.status_code,
              ms=round(1000 * (time.monotonic() - started)))
    return response


@app.middleware("http")
async def refuse_large_bodies(request: Request, call_next):
    """Refuse a body that says it is over MAX_UPLOAD_BYTES (plus room for the form fields) before
    any of it is read; save_wav still checks the file itself."""
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > MAX_UPLOAD_BYTES + 64 * 1024:
        log.event("refused", path=request.url.path, status=413, code="file_too_large")
        return JSONResponse({"error": "file_too_large", "message": f"the upload is over {MAX_UPLOAD_BYTES // 2**20} MB"},
                            status_code=413)
    return await call_next(request)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def public(user):
    """The user as the app sees it. The voice embedding itself never leaves the server."""
    return {**{key: user[key] for key in ("id", "name", "email", "language", "consent_given_at",
                                          "caregiver_name", "caregiver_phone")},
            "has_own_voice": user["voice_embedding"] is not None, "use_own_voice": bool(user["use_own_voice"]),
            "can_clone_voice": user["language"] in speak.CLONE_LANGUAGES,
            "phrase_goal": int(user["phrase_goal"]) if user.get("phrase_goal") is not None else None}


def get_user(user_id):
    return db.row("SELECT * FROM users WHERE id = ?", (user_id,))


def current_user(sunn_session: str | None = Cookie(None)):
    """The signed-in user from the session cookie. Every per-user route depends on this, so
    nobody can reach another person's data by changing an id."""
    user_id = auth.user_id_from_token(sunn_session) if sunn_session else None
    user = get_user(user_id) if user_id else None
    if user is None:
        raise Refused(401, "not_logged_in", "not signed in")
    return user


def owned(table, row_id, user_id):
    """A row of table that belongs to user_id, else 404, whether it is missing or someone else's."""
    found = db.row(f"SELECT * FROM {table} WHERE id = ? AND user_id = ?", (row_id, user_id))
    if found is None:
        raise Refused(404, "not_found", f"{table.rstrip('s').replace('_', ' ')} not found")
    return found


def clean_text(text):
    text = " ".join(str(text).split())
    if not text:
        raise Refused(400, "invalid_input", "text is empty")
    return text


def contexts_column(contexts):
    """["home", "market"] -> "home,market"; an empty list means any."""
    return ",".join(dict.fromkeys(contexts)) or "any"


def phrase_out(phrase):
    return {**phrase, "contexts": phrase["contexts"].split(","), "urgent": bool(phrase["urgent"])}


def get_phrase(user_id, phrase_id):
    phrase = owned("phrases", phrase_id, user_id)
    return phrase_out({key: phrase[key] for key in ("id", "text", "contexts", "urgent", "language")})


def find_or_add_phrase(user, text):
    """Phrase id for text in the user's language, reusing an identical phrase so one phrase never
    splits the bank. The same words in another language are another phrase."""
    text = clean_text(text)
    phrase = db.row("SELECT id FROM phrases WHERE user_id = ? AND text = ? AND language = ?",
                    (user["id"], text, user["language"]))
    if phrase:
        return phrase["id"]
    return db.execute("INSERT INTO phrases (user_id, text, language) VALUES (?, ?, ?)",
                      (user["id"], text, user["language"]))


def user_folder(user):
    return f"{USERS_DIR}/{user['id']}"


def voice_folder(user):
    """The cloned voice's cache: Gnani's embedding for the reference audio, and every phrase
    spoken in that voice. Deleted with the voice."""
    return f"{user_folder(user)}/voice"


def save_wav(upload, folder, limits, rate=16000):
    """Store the upload in folder as a wav (see audio.to_wav) and return its path. Refuses a
    file over MAX_UPLOAD_BYTES or a recording outside limits, (min, max) seconds."""
    data = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) == 0:
        raise Refused(400, "bad_audio", "the audio file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise Refused(413, "file_too_large", f"the audio file is over {MAX_UPLOAD_BYTES // 2**20} MB")
    os.makedirs(folder, exist_ok=True)
    name = uuid.uuid4().hex
    raw, wav = f"{folder}/{name}.upload", f"{folder}/{name}.wav"
    with open(raw, "wb") as f:
        f.write(data)
    try:
        audio.to_wav(raw, wav, rate)
    except subprocess.CalledProcessError:
        raise Refused(400, "bad_audio", "could not read the audio file")
    finally:
        os.remove(raw)
    seconds, (low, high) = audio.seconds(wav) or 0.0, limits
    if not low <= seconds <= high:
        os.remove(wav)
        raise Refused(400, "audio_too_short" if seconds < low else "audio_too_long",
                      f"the recording is {seconds:.1f} s; it needs {low} to {high} s", seconds=round(seconds, 1))
    return wav


def save_and_transcribe(user, upload, quota="stt"):
    """Store a phrase-length upload under data/users/<id>/; returns (path, Prisma hypothesis).
    Nothing is kept when Prisma fails or hears no speech. quota is the daily limit it counts against."""
    wav = save_wav(upload, user_folder(user), PHRASE_SECONDS)
    try:
        hypothesis = prisma.transcribe(wav, user["language"], user["id"], quota)
    except gnani.GnaniError:
        os.remove(wav)
        raise
    if not hypothesis.strip():
        os.remove(wav)
        raise Refused(422, "no_speech", "no speech was heard in the recording")
    return wav, hypothesis


def remove_audio(samples):
    """Delete samples' recordings and their cached Prisma transcripts, each cached under the
    language it was transcribed in."""
    for sample in samples:
        path = sample["audio_path"]
        if os.path.exists(path):
            with open(path, "rb") as f:
                cached = prisma.cache_path(f.read(), sample["language"])
            if os.path.exists(cached):
                os.remove(cached)
            os.remove(path)


def audio_samples(user, column, value):
    return db.rows(f"SELECT audio_path, language FROM samples WHERE user_id = ? AND {column} = ?", (user["id"], value))


def enroll_sample(user, upload, column, value, source=None):
    """Record an enrollment sample for a phrase, slot word or template fixed part. source says
    where a demo recording came from (pilot, torgo, simulated); None for one made in the app."""
    path, hypothesis = save_and_transcribe(user, upload, "enroll")
    sample_id = db.execute(
        f"INSERT INTO samples (user_id, {column}, audio_path, prisma_hypothesis, source, created_at, language,"
        " speech_source) VALUES (?, ?, ?, ?, 'enroll', ?, ?, ?)",
        (user["id"], value, path, hypothesis, now(), user["language"], source))
    return {"sample_id": sample_id, column: value, "hypothesis": hypothesis, "source": source}


def add_template(user_id, text):
    text = " ".join(text.split())
    parsed = matcher.parse_template(text)
    if parsed is None:
        raise Refused(400, "invalid_input", "a template has one {item}, {person} or {place}, at its start or end,"
                                           " and at least one other word")
    found = db.row("SELECT id FROM templates WHERE user_id = ? AND text = ?", (user_id, text))
    if found:
        return found["id"]
    return db.execute("INSERT INTO templates (user_id, text, fixed_part) VALUES (?, ?, ?)", (user_id, text, parsed[1]))


def add_slot_word(user_id, slot, text):
    text = clean_text(text)
    found = db.row("SELECT id FROM slot_words WHERE user_id = ? AND slot = ? AND text = ?", (user_id, slot, text))
    if found:
        return found["id"]
    return db.execute("INSERT INTO slot_words (user_id, slot, text) VALUES (?, ?, ?)", (user_id, slot, text))


def add_default_building_blocks(user_id, language):
    """The default slot words and templates for language, in one transaction; ones the user
    already has are skipped."""
    words = {(w["slot"], w["text"]) for w in db.rows("SELECT slot, text FROM slot_words WHERE user_id = ?", (user_id,))}
    templates = {t["text"] for t in db.rows("SELECT text FROM templates WHERE user_id = ?", (user_id,))}
    statements = [("INSERT INTO slot_words (user_id, slot, text) VALUES (?, ?, ?)", (user_id, slot, word))
                  for slot, slot_words in DEFAULT_SLOT_WORDS.get(language, {}).items() for word in slot_words
                  if (slot, word) not in words]
    statements += [("INSERT INTO templates (user_id, text, fixed_part) VALUES (?, ?, ?)",
                    (user_id, text, matcher.parse_template(text)[1]))
                   for text in DEFAULT_TEMPLATES.get(language, []) if text not in templates]
    if statements:
        db.transaction(*statements)


def trust_proxy():
    """TRUST_PROXY: on when the app runs behind a proxy that sets X-Forwarded-For (docs/DEPLOY.md)."""
    return os.environ.get("TRUST_PROXY", "").strip().lower() in ("1", "true", "yes", "on")


gnani_mock.check_startup(trust_proxy())  # never mock behind a proxy, and say so loudly when on
gnani.check_startup()  # no key in real mode: fail now, not on the first call
reranker.load()  # once, and only when RERANKER_ENABLED; a missing model is a warning


def client_ip(request):
    """The address new accounts are counted by. Behind a proxy every request arrives from the
    proxy, so with TRUST_PROXY on it is the left-most X-Forwarded-For entry, the client as the
    proxy saw it; otherwise the socket's own peer."""
    if trust_proxy():
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else None


def check_signup_rate(request):
    """At most auth.MAX_SIGNUPS new accounts per IP an hour, by email or Google."""
    wait = auth.seconds_locked(("signup", client_ip(request)), auth.MAX_SIGNUPS, auth.SIGNUP_WINDOW)
    if wait:
        raise Refused(429, "too_many_attempts", "too many new accounts from this address, try again later",
                      retry_after=wait)


def new_account(request, response, user_id, language, event):
    """What every sign-up does once the user row exists."""
    auth.record_failure(("signup", client_ip(request)))
    add_default_building_blocks(user_id, language)
    auth.set_session(response, user_id)
    log.event(event, user_id=user_id)
    return public(get_user(user_id))


@app.post("/auth/signup", response_model=schemas.User)
def signup(body: schemas.Signup, request: Request, response: Response):
    name, email, password, language = body.name.strip(), body.email.strip().lower(), body.password, body.language
    check_signup_rate(request)
    if not body.consent:
        raise Refused(400, "consent_required", "consent must be true")
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
    return new_account(request, response, user_id, language, "signup")


@app.post("/auth/login", response_model=schemas.User)
def login(body: schemas.Login, response: Response):
    email, password = body.email.strip().lower(), body.password
    wait = auth.seconds_locked(email)
    if wait:
        raise Refused(429, "too_many_attempts", "too many failed attempts, try again later", retry_after=wait)
    user = db.row("SELECT * FROM users WHERE email = ?", (email,))
    if user is None:
        raise Refused(401, "no_account", "no account with this email")
    if not auth.check_password(user["password_hash"], password):
        auth.record_failure(email)
        raise Refused(401, "bad_login", "wrong password")
    auth.clear_failures(email)
    auth.set_session(response, user["id"])
    log.event("login", user_id=user["id"])
    return public(user)


@app.post("/auth/google", response_model=schemas.User)
def auth_google(body: schemas.GoogleAuth, request: Request, response: Response):
    """Authenticate or register with a Google Identity Services ID token."""
    token = body.id_token.strip()
    if not token:
        raise Refused(400, "invalid_google_token", "Google ID token is required")

    google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    try:
        res = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token},
            timeout=5,
        )
    except Exception:
        log.event("google_auth_failed", level=logging.WARNING, reason="network_error")
        raise Refused(502, "google_unreachable", "could not reach Google verification services")

    if res.status_code != 200:
        raise Refused(401, "invalid_google_token", "invalid or expired Google token")

    payload = res.json()
    issuer = payload.get("iss", "")
    if issuer not in ("accounts.google.com", "https://accounts.google.com"):
        raise Refused(401, "invalid_google_token", "unrecognized token issuer")

    aud = payload.get("aud", "")
    if google_client_id and aud != google_client_id:
        log.event("google_auth_failed", level=logging.WARNING, reason="audience_mismatch", aud=aud)
        raise Refused(401, "invalid_google_token", "token was not issued for this application")

    email = (payload.get("email") or "").strip().lower()
    if not email or not EMAIL.fullmatch(email):
        raise Refused(400, "bad_email", "invalid email in Google token")

    verified = str(payload.get("email_verified", "")).lower() == "true"
    if not verified:
        raise Refused(400, "unverified_email", "Google email is not verified")

    google_id = str(payload.get("sub", "")).strip()
    name = (payload.get("name") or payload.get("given_name") or email.split("@")[0]).strip()

    user = None
    if google_id:
        user = db.row("SELECT * FROM users WHERE google_id = ?", (google_id,))
    if not user:
        user = db.row("SELECT * FROM users WHERE email = ?", (email,))

    if user:
        if google_id and not user["google_id"]:
            db.execute("UPDATE users SET google_id = ? WHERE id = ?", (google_id, user["id"]))
            user = get_user(user["id"])
        auth.set_session(response, user["id"])
        log.event("login_google", user_id=user["id"])
        return public(user)

    check_signup_rate(request)
    if not body.consent:
        raise Refused(400, "consent_required", "consent must be true")
    language = body.language if body.language in languages.CODES else "en"
    try:
        user_id = db.execute(
            "INSERT INTO users (name, email, password_hash, language, consent_given_at, google_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, "oauth:google", language, now(), google_id or None),
        )
    except sqlite3.IntegrityError:
        raise Refused(409, "email_taken", "an account with this email already exists")
    return new_account(request, response, user_id, language, "signup_google")


@app.post("/auth/logout", response_model=schemas.Ok)
def logout(response: Response):
    auth.clear_session(response)
    return {"ok": True}


@app.get("/auth/me", response_model=schemas.User)
def me(user=Depends(current_user)):
    return public(user)


@app.patch("/me", response_model=schemas.User)
def update_me(changes: schemas.UserUpdate, user=Depends(current_user)):
    """Change any of use_own_voice (needs a recorded voice), caregiver_name and caregiver_phone
    (digits with the country code, like 919876543210; spaces, dashes and + are dropped).
    null or "" clears a caregiver field. language (languages.CODES) is what Prisma hears from now on
    and new phrases are in; nothing is deleted, but the matcher only uses phrases and samples in
    the current language and English."""
    updates = {}
    for field, value in changes.model_dump(exclude_unset=True).items():
        if field == "language" and value is not None:
            updates[field] = value
        elif field == "use_own_voice" and value is not None:
            if value and user["voice_embedding"] is None:
                raise Refused(409, "no_voice", "record your voice first")
            updates[field] = int(value)
        elif field == "phrase_goal" and value is not None:
            if value < 1:
                raise Refused(400, "invalid_input", "phrase_goal must be at least 1")
            updates[field] = int(value)
        elif field in ("caregiver_name", "caregiver_phone"):
            value = " ".join((value or "").split()) or None
            if field == "caregiver_phone" and value:
                value = re.sub(r"[\s\-()+]", "", value)
                if not PHONE.fullmatch(value):
                    raise Refused(400, "invalid_input", "caregiver_phone is digits with the country code, like 919876543210")
            updates[field] = value
    if updates:
        db.execute(f"UPDATE users SET {', '.join(f'{field} = ?' for field in updates)} WHERE id = ?",
                   (*updates.values(), user["id"]))
    if "language" in updates and updates["language"] != user["language"]:
        log.event("language_changed", user_id=user["id"], language=updates["language"])
    return public(get_user(user["id"]))


@app.delete("/me", response_model=schemas.Ok)
def delete_me(response: Response, user=Depends(current_user)):
    """Delete the account and everything it made: phrases, slot words, templates, samples, uses,
    every recording and its cached Prisma transcript, and the cloned voice with everything
    spoken in it. Files go first, so a failure leaves the account in place to try again.
    Kept: the stock-voice Timbre cache (phrase text spoken by Nalini or Kaveri, shared by
    everyone who says it, not tied to anyone) and api_calls (counts only)."""
    remove_audio(db.rows("SELECT audio_path, language FROM samples WHERE user_id = ?", (user["id"],)))
    if os.path.exists(user_folder(user)):
        shutil.rmtree(user_folder(user))
    db.delete_user(user["id"])
    auth.clear_session(response)
    log.event("account_deleted", user_id=user["id"])
    return {"ok": True}


@app.post("/me/voice", response_model=schemas.User)
def set_voice(audio_file: UploadFile = File(alias="audio"), consent: str = Form(""), user=Depends(current_user)):
    """Clone the user's voice from 5-30 s of their speech (the docs' range). Needs consent=true.
    Only Gnani's embedding is kept; the recording is deleted once it is made."""
    if consent.strip().lower() != "true":
        raise Refused(400, "consent_required", "consent must be true to clone your voice")
    # The docs ask only for WAV or MP3; 44.1 kHz keeps more of the voice than Prisma's 16 kHz.
    wav = save_wav(audio_file, voice_folder(user), VOICE_SECONDS, rate=44100)
    try:
        embedding = speak.clone_voice(wav, voice_folder(user), user["id"])
    finally:
        os.remove(wav)
    db.execute("UPDATE users SET voice_embedding = ?, voice_consent_given_at = ? WHERE id = ?",
               (json.dumps(embedding), now(), user["id"]))
    log.event("voice_cloned", user_id=user["id"])
    return public(get_user(user["id"]))


@app.delete("/me/voice", response_model=schemas.User)
def delete_voice(user=Depends(current_user)):
    """Forget the cloned voice: its embedding, its cache and every phrase spoken in it."""
    if os.path.exists(voice_folder(user)):
        shutil.rmtree(voice_folder(user))
    db.execute("UPDATE users SET voice_embedding = NULL, voice_consent_given_at = NULL, use_own_voice = 0"
               " WHERE id = ?", (user["id"],))
    log.event("voice_deleted", user_id=user["id"])
    return public(get_user(user["id"]))


@app.get("/me/phrases", response_model=list[schemas.PhraseDetail])
def list_phrases(user=Depends(current_user)):
    """Every phrase, in every language, with its enrollment recordings (enrolled, so enrollment can
    resume), its samples in the user's current language or English (sample_count, confirmed
    recognitions included; the matcher ignores the rest), when it was last used, and sources: where
    its demo recordings came from (pilot, torgo, simulated; empty when every recording was made in
    the app)."""
    return [{**phrase_out(p), "sources": sorted(p["sources"].split(",")) if p["sources"] else []}
            for p in db.rows("""
        SELECT p.id, p.text, p.contexts, p.urgent, p.language,
            (SELECT COUNT(*) FROM samples s WHERE s.phrase_id = p.id AND s.source = 'enroll') AS enrolled,
            (SELECT COUNT(*) FROM samples s WHERE s.phrase_id = p.id AND s.language IN (:language, 'en'))
                AS sample_count,
            (SELECT MAX(created_at) FROM uses u WHERE u.phrase_id = p.id) AS last_used_at,
            (SELECT GROUP_CONCAT(DISTINCT s.speech_source) FROM samples s WHERE s.phrase_id = p.id) AS sources
        FROM phrases p WHERE p.user_id = :u ORDER BY p.id""", {"u": user["id"], "language": user["language"]})]


@app.post("/me/phrases", response_model=schemas.Phrase)
def add_phrase(body: schemas.NewPhrase, user=Depends(current_user)):
    return get_phrase(user["id"], find_or_add_phrase(user, body.text))


@app.post("/me/phrases/default", response_model=list[schemas.PhraseDetail])
def add_default_phrases(user=Depends(current_user)):
    """Add the everyday phrases in the user's language (data/default_phrases_<code>.txt; past
    Hindi and English, each line is "phrase | Latin spelling | English meaning"), with contexts
    from their group comment (GROUP_CONTEXTS; a group not listed there is any), and the default
    slot words and templates for it. Text the user already has in that language is skipped, so
    after a language change this adds the new language's. One transaction for all of them: one
    commit instead of one per phrase, which kept sign-up waiting for seconds."""
    language = user["language"]
    add_default_building_blocks(user["id"], language)
    have = {p["text"] for p in db.rows("SELECT text FROM phrases WHERE user_id = ? AND language = ?",
                                       (user["id"], language))}
    contexts, statements = "any", []
    with open(DEFAULT_PHRASES.format(language=language), encoding="utf-8") as f:
        for line in f:
            text, *gloss = [" ".join(part.split()) for part in line.split("|")]
            if line.startswith("#"):
                contexts = GROUP_CONTEXTS.get(line.strip("# \n"), "any")
            elif text and text not in have:
                have.add(text)
                urgent = text in URGENT_PHRASES or bool(gloss) and gloss[-1] in URGENT_PHRASES
                statements.append(("INSERT INTO phrases (user_id, text, contexts, urgent, language)"
                                   " VALUES (?, ?, ?, ?, ?)", (user["id"], text, contexts, int(urgent), language)))
    if statements:
        db.transaction(*statements)
    return list_phrases(user)


@app.patch("/me/phrases/{phrase_id}", response_model=schemas.Phrase)
def update_phrase(phrase_id: int, changes: schemas.PhraseUpdate, user=Depends(current_user)):
    """Change any of text, contexts (a list) and urgent (true or false); null leaves one as it is."""
    get_phrase(user["id"], phrase_id)
    updates = {}
    for field, value in changes.model_dump(exclude_none=True).items():
        if field == "text":
            updates[field] = clean_text(value)
            taken = db.row("SELECT id FROM phrases WHERE user_id = ? AND text = ? AND id != ? AND language ="
                           " (SELECT language FROM phrases WHERE id = ?)", (user["id"], updates[field], phrase_id, phrase_id))
            if taken:
                raise Refused(409, "phrase_exists", "another phrase already has this text", phrase_id=taken["id"])
        elif field == "contexts":
            updates[field] = contexts_column(value)
        elif field == "urgent":
            updates[field] = int(value)
    if updates:
        db.execute(f"UPDATE phrases SET {', '.join(f'{field} = ?' for field in updates)} WHERE id = ? AND user_id = ?",
                   (*updates.values(), phrase_id, user["id"]))
    return get_phrase(user["id"], phrase_id)


@app.delete("/me/phrases/{phrase_id}", response_model=schemas.Ok)
def delete_phrase(phrase_id: int, user=Depends(current_user)):
    """Delete a phrase, its samples with their recordings, and its uses."""
    get_phrase(user["id"], phrase_id)
    samples = audio_samples(user, "phrase_id", phrase_id)
    db.transaction(("DELETE FROM samples WHERE phrase_id = ? AND user_id = ?", (phrase_id, user["id"])),
                   ("UPDATE samples SET top1_phrase_id = NULL WHERE top1_phrase_id = ? AND user_id = ?", (phrase_id, user["id"])),
                   ("DELETE FROM uses WHERE phrase_id = ? AND user_id = ?", (phrase_id, user["id"])),
                   ("DELETE FROM phrases WHERE id = ? AND user_id = ?", (phrase_id, user["id"])))
    remove_audio(samples)
    return {"ok": True}


@app.delete("/me/samples/{sample_id}", response_model=schemas.Ok)
def delete_sample(sample_id: int, user=Depends(current_user)):
    sample = owned("samples", sample_id, user["id"])
    db.execute("DELETE FROM samples WHERE id = ? AND user_id = ?", (sample_id, user["id"]))
    remove_audio([sample])
    return {"ok": True}


@app.post("/me/enroll", response_model=schemas.Enrolled)
def enroll(phrase_id: int = Form(), audio_file: UploadFile = File(alias="audio"),
           source: schemas.SpeechSource | None = Form(None), user=Depends(current_user)):
    """source is only for demo recordings (scripts/load_demo.py); the app leaves it out."""
    get_phrase(user["id"], phrase_id)
    return enroll_sample(user, audio_file, "phrase_id", phrase_id, source)


@app.get("/me/slot-words", response_model=list[schemas.SlotWord])
def list_slot_words(user=Depends(current_user)):
    return db.rows("SELECT w.id, w.slot, w.text, COUNT(s.id) AS enrolled FROM slot_words w"
                   " LEFT JOIN samples s ON s.slot_word_id = w.id"
                   " WHERE w.user_id = ? GROUP BY w.id ORDER BY w.id", (user["id"],))


@app.post("/me/slot-words", response_model=schemas.SlotWord)
def create_slot_word(body: schemas.NewSlotWord, user=Depends(current_user)):
    slot_word_id = add_slot_word(user["id"], body.slot, body.text)
    return next(w for w in list_slot_words(user) if w["id"] == slot_word_id)


@app.delete("/me/slot-words/{slot_word_id}", response_model=schemas.Ok)
def delete_slot_word(slot_word_id: int, user=Depends(current_user)):
    owned("slot_words", slot_word_id, user["id"])
    samples = audio_samples(user, "slot_word_id", slot_word_id)
    db.transaction(("DELETE FROM samples WHERE slot_word_id = ? AND user_id = ?", (slot_word_id, user["id"])),
                   ("DELETE FROM slot_words WHERE id = ? AND user_id = ?", (slot_word_id, user["id"])))
    remove_audio(samples)
    return {"ok": True}


@app.post("/me/slot-words/{slot_word_id}/enroll", response_model=schemas.Enrolled)
def enroll_slot_word(slot_word_id: int, audio_file: UploadFile = File(alias="audio"),
                     source: schemas.SpeechSource | None = Form(None), user=Depends(current_user)):
    owned("slot_words", slot_word_id, user["id"])
    return enroll_sample(user, audio_file, "slot_word_id", slot_word_id, source)


@app.get("/me/templates", response_model=list[schemas.Template])
def list_templates(user=Depends(current_user)):
    """Each template with its slot and fixed_part: the words recorded on their own."""
    templates = db.rows("SELECT t.id, t.text, t.fixed_part, COUNT(s.id) AS enrolled FROM templates t"
                        " LEFT JOIN samples s ON s.template_id = t.id"
                        " WHERE t.user_id = ? GROUP BY t.id ORDER BY t.id", (user["id"],))
    return [{**t, "slot": matcher.parse_template(t["text"])[0]} for t in templates]


@app.post("/me/templates", response_model=schemas.Template)
def create_template(body: schemas.NewTemplate, user=Depends(current_user)):
    template_id = add_template(user["id"], body.text)
    return next(t for t in list_templates(user) if t["id"] == template_id)


@app.delete("/me/templates/{template_id}", response_model=schemas.Ok)
def delete_template(template_id: int, user=Depends(current_user)):
    owned("templates", template_id, user["id"])
    samples = audio_samples(user, "template_id", template_id)
    db.transaction(("DELETE FROM samples WHERE template_id = ? AND user_id = ?", (template_id, user["id"])),
                   ("DELETE FROM templates WHERE id = ? AND user_id = ?", (template_id, user["id"])))
    remove_audio(samples)
    return {"ok": True}


@app.post("/me/templates/{template_id}/enroll", response_model=schemas.Enrolled)
def enroll_template(template_id: int, audio_file: UploadFile = File(alias="audio"),
                    source: schemas.SpeechSource | None = Form(None), user=Depends(current_user)):
    """A recording of the template's fixed part alone, like "चाहिए" for "{item} चाहिए"."""
    owned("templates", template_id, user["id"])
    return enroll_sample(user, audio_file, "template_id", template_id, source)


def candidates_for(user):
    """What a recording can be matched to: every phrase in the user's language, or English, and
    every template × slot word of its slot. A recording is transcribed in the user's language, so
    only samples in that language (or English) are fingerprints: Prisma's hi-IN and ta-IN
    hypotheses of the same speech aren't comparable. A composition's fingerprints are each slot
    word hypothesis joined to each fixed part hypothesis, in the template's word order. A
    composition whose text is already a phrase adds its fingerprints to that phrase instead of
    standing on its own."""
    user_id, heard, spoken = user["id"], defaultdict(list), (user["language"], "en")
    for s in db.rows("SELECT phrase_id, slot_word_id, template_id, prisma_hypothesis FROM samples"
                     " WHERE user_id = ? AND source IS NOT NULL AND language IN (?, ?)", (user_id, *spoken)):
        for column in ("phrase_id", "slot_word_id", "template_id"):
            if s[column] is not None:
                heard[column, s[column]].append(s["prisma_hypothesis"])

    candidates = {}
    for p in db.rows("SELECT id, text, contexts, urgent FROM phrases WHERE user_id = ? AND language IN (?, ?)"
                     " ORDER BY language != 'en', id", (user_id, *spoken)):
        candidates[p["text"]] = {"key": p["id"], "phrase_id": p["id"], "text": p["text"], "composed": False,
                                 "contexts": p["contexts"].split(","), "urgent": bool(p["urgent"]),
                                 "fingerprints": heard["phrase_id", p["id"]]}
    words = db.rows("SELECT id, slot, text FROM slot_words WHERE user_id = ?", (user_id,))
    for t in db.rows("SELECT id, text, fixed_part FROM templates WHERE user_id = ?", (user_id,)):
        slot, _, slot_first = matcher.parse_template(t["text"])
        for w in (w for w in words if w["slot"] == slot):
            fingerprints = [matcher.compose(slot_first, word, fixed)
                            for word in heard["slot_word_id", w["id"]] for fixed in heard["template_id", t["id"]]]
            text = matcher.compose(slot_first, w["text"], t["fixed_part"])
            if text in candidates:
                candidates[text]["fingerprints"] = candidates[text]["fingerprints"] + fingerprints
            else:
                candidates[text] = {"key": None, "phrase_id": None, "text": text, "composed": True,
                                    "template_id": t["id"], "slot_word_id": w["id"], "contexts": [],
                                    "urgent": False, "fingerprints": fingerprints}
    return list(candidates.values())


def priors_for(user_id):
    uses = [(u["phrase_id"], datetime.fromisoformat(u["created_at"]))
            for u in db.rows("SELECT phrase_id, created_at FROM uses WHERE user_id = ?", (user_id,))]
    return matcher.usage_priors(uses, matcher.time_bucket(datetime.now(timezone.utc)))


def history_for(user_id):
    """(the last 3 phrases the user spoke, newest first; {phrase_id: times used}), for the judge."""
    uses = db.rows("SELECT u.phrase_id, p.text FROM uses u JOIN phrases p ON p.id = u.phrase_id"
                   " WHERE u.user_id = ? ORDER BY u.created_at DESC, u.id DESC", (user_id,))
    return [u["text"] for u in uses[:3]], Counter(u["phrase_id"] for u in uses)


@contextmanager
def timer(timings, step):
    started = time.monotonic()
    yield
    timings[step] = round(1000 * (time.monotonic() - started))


@app.post("/me/recognize", response_model=schemas.Recognition)
def recognize(audio_file: UploadFile = File(alias="audio"), context: schemas.Context | None = Form(None),
              ui_language: schemas.Language = Form("en"), user=Depends(current_user)):
    """Top 3 candidates for a recording. Each has score = similarity + context + freq + time
    (see matcher.py), + rerank when RERANKER_ENABLED and the user speaks Hindi (src/reranker.py),
    with those parts, urgent, and composed: a composed one is a template × slot word that isn't a
    phrase yet, with its template_id and slot_word_id. When LLM_ENABLED, the judge
    (src/llm_judge.py) may put another of the top 5 first: chosen_by says which did, and reason is
    the judge's when it did, in ui_language (the interface's) or null when it isn't readable."""
    timings = {"stt": None, "match": None, "rerank": None, "llm": None, "tts": None}  # tts: POST /speak
    with timer(timings, "stt"):
        path, hypothesis = save_and_transcribe(user, audio_file)
    with timer(timings, "match"):
        ranked = matcher.rank(hypothesis, candidates_for(user), context, priors_for(user["id"]), k=reranker.SHORTLIST)
    if reranker.on() and user["language"] in reranker.LANGUAGES:
        with timer(timings, "rerank"):
            ranked = reranker.rescore(hypothesis, ranked)
    judged = {"shown": ranked[:llm_judge.SHOWN], "chosen_by": "matcher", "reason": None}
    if llm_judge.should_ask(hypothesis, ranked):
        with timer(timings, "llm"):
            judged = llm_judge.judge(hypothesis, ranked, context, *history_for(user["id"]), user["id"],
                                     user["language"], ui_language)
    candidates = [{key: c[key] for key in ("phrase_id", "text", "score", "parts", "urgent", "composed",
                                           "template_id", "slot_word_id") if key in c} for c in judged["shown"]]
    sample_id = db.execute(
        "INSERT INTO samples (user_id, audio_path, prisma_hypothesis, top1_phrase_id, created_at, language)"
        " VALUES (?, ?, ?, ?, ?, ?)", (user["id"], path, hypothesis, candidates[0]["phrase_id"] if candidates else None,
                                       now(), user["language"]))
    return {
        "sample_id": sample_id,
        "hypothesis": hypothesis,
        "context": context,
        "candidates": candidates,
        "low_confidence": not candidates or candidates[0]["parts"]["similarity"] < matcher.LOW_CONFIDENCE,
        "chosen_by": judged["chosen_by"],
        "reason": judged["reason"],
        "timings_ms": timings,
    }


@app.post("/me/confirm", response_model=schemas.Confirmed)
def confirm(body: schemas.Confirm, user=Depends(current_user)):
    """Say what a recognition was: a phrase_id, a new_text, or a composed candidate's
    template_id and slot_word_id (which makes it a real phrase). Logs one use."""
    user_id, sample_id, phrase_id, new_text = user["id"], body.sample_id, body.phrase_id, body.new_text
    template_id, slot_word_id = body.template_id, body.slot_word_id
    composed = template_id is not None or slot_word_id is not None
    if [phrase_id is not None, new_text is not None, composed].count(True) != 1 or \
            composed and (template_id is None or slot_word_id is None):
        raise Refused(400, "invalid_input", "send one of phrase_id, new_text, or template_id with slot_word_id")
    if owned("samples", sample_id, user_id)["source"] == "enroll":
        raise Refused(404, "not_found", "recognition sample not found")

    if composed:
        template, word = owned("templates", template_id, user_id), owned("slot_words", slot_word_id, user_id)
        slot, fixed, slot_first = matcher.parse_template(template["text"])
        if word["slot"] != slot:
            raise Refused(400, "invalid_input", f"that template takes a {slot}")
        new_text = matcher.compose(slot_first, word["text"], fixed)
    phrase = get_phrase(user_id, find_or_add_phrase(user, new_text) if new_text is not None else phrase_id)
    db.transaction(("UPDATE samples SET phrase_id = ?, source = 'correction' WHERE id = ?", (phrase["id"], sample_id)),
                   ("INSERT INTO uses (user_id, phrase_id, created_at) VALUES (?, ?, ?)", (user_id, phrase["id"], now())))
    return {"sample_id": sample_id, "phrase_id": phrase["id"], "text": phrase["text"], "urgent": phrase["urgent"]}


@app.post("/speak", response_class=FileResponse, responses={200: {"content": {"audio/wav": {}}}})
def speak_text(body: schemas.Speak, user=Depends(current_user)):
    """Say text in its phrase's language (their phrase in the language they speak first; the
    user's language when it is no phrase), in the user's cloned voice when use_own_voice is on and
    that language offers it (speak.CLONE_LANGUAGES), else in the language's stock voice. Answers
    audio/wav, with how long Timbre took in Server-Timing."""
    text, timings = clean_text(body.text), {}
    phrase = db.row("SELECT language FROM phrases WHERE user_id = ? AND text = ? ORDER BY language = ? DESC,"
                    " language = 'en' DESC LIMIT 1", (user["id"], text, user["language"]))
    language = body.language if (body.language and body.language in languages.CODES) else (phrase["language"] if phrase else user["language"])
    with timer(timings, "tts"):
        if user["use_own_voice"] and user["voice_embedding"] and language in speak.CLONE_LANGUAGES:
            path = speak.synthesize(text, language, json.loads(user["voice_embedding"]),
                                    cache_dir=f"{voice_folder(user)}/tts", user_id=user["id"])
        else:
            path = speak.synthesize(text, language, user_id=user["id"])
    return FileResponse(path, media_type="audio/wav", headers={"Server-Timing": f"tts;dur={timings['tts']}"})


@app.get("/me/stats", response_model=schemas.Stats)
def stats(user=Depends(current_user)):
    """Counts (samples are enrollments plus confirmed recognitions), the top 5 phrases by use,
    and clear_without_help_by_week: for each of the last 8 weeks (Monday first, oldest first), the
    share of confirmed recognitions whose raw Prisma hypothesis was already within
    CLEAR_SIMILARITY (90 of 100) of the phrase. A rough trend of how often the speech service
    understood without the personal layer, not a medical measure of speech."""
    counts = db.row("""
        SELECT
            (SELECT COUNT(*) FROM phrases WHERE user_id = :u) AS phrases,
            COUNT(*) FILTER (WHERE source IS NOT NULL) AS samples,
            COUNT(*) FILTER (WHERE source = 'enroll') AS enroll_samples,
            COUNT(*) FILTER (WHERE source IS NOT 'enroll') AS recognitions,
            COUNT(*) FILTER (WHERE source = 'correction') AS confirmed,
            COUNT(*) FILTER (WHERE source = 'correction' AND phrase_id = top1_phrase_id) AS top1_hits
        FROM samples WHERE user_id = :u""", {"u": user["id"]})
    confirmed = counts["confirmed"]
    counts["top1_hit_rate"] = round(counts["top1_hits"] / confirmed, 3) if confirmed else None

    today = datetime.now().astimezone().date()
    this_week = today - timedelta(days=today.weekday())
    weeks = {this_week - timedelta(weeks=n): [0, 0] for n in range(7, -1, -1)}  # start -> [confirmed, clear]
    for s in db.rows("SELECT s.prisma_hypothesis, s.created_at, p.text FROM samples s JOIN phrases p"
                     " ON p.id = s.phrase_id WHERE s.user_id = ? AND s.source = 'correction'", (user["id"],)):
        day = datetime.fromisoformat(s["created_at"]).astimezone().date()
        week = weeks.get(day - timedelta(days=day.weekday()))
        if week:
            week[0] += 1
            week[1] += matcher.similarity(s["prisma_hypothesis"], s["text"]) >= matcher.CLEAR_SIMILARITY
    counts["clear_without_help_by_week"] = [
        {"week_start": start.isoformat(), "confirmed": n, "clear": clear, "rate": round(clear / n, 3) if n else None}
        for start, (n, clear) in weeks.items()]
    counts["top_phrases"] = db.rows(
        "SELECT p.id AS phrase_id, p.text, COUNT(*) AS uses FROM uses u JOIN phrases p ON p.id = u.phrase_id"
        " WHERE u.user_id = ? GROUP BY p.id ORDER BY uses DESC, MAX(u.created_at) DESC LIMIT 5", (user["id"],))
    return counts


@app.get("/me/usage", response_model=schemas.MyUsage)
def my_usage(user=Depends(current_user)):
    """This account's Gnani calls in the last 24 hours against each daily limit (see gnani.LIMITS)."""
    return gnani.usage(user["id"])


@app.get("/admin/usage", response_model=schemas.Usage)
def usage(user=Depends(current_user)):
    """Gnani calls by everyone, against GNANI_CALL_LIMIT. Only for the owner: the account whose
    email is OWNER_EMAIL in .env."""
    owner = os.environ.get("OWNER_EMAIL", "").strip().lower()
    if not owner or user["email"] != owner:
        raise Refused(403, "not_owner", "only the owner (OWNER_EMAIL in .env) can see usage")
    by_kind = {r.pop("kind"): r for r in db.rows(
        "SELECT kind, SUM(cached = 0) AS sent, SUM(cached) AS cached,"
        " ROUND(TOTAL(CASE WHEN cached = 0 THEN audio_seconds END), 1) AS sent_audio_seconds"
        " FROM api_calls GROUP BY kind")}
    sent, limit = sum(r["sent"] for r in by_kind.values()), gnani.call_limit()
    return {"limit": limit, "sent": sent, "remaining": max(0, limit - sent), "by_kind": by_kind}


@app.get("/auth/google/config", response_model=schemas.GoogleConfig)
def google_config():
    """Google OAuth client ID for Google Identity Services; empty when unconfigured."""
    return {"client_id": os.environ.get("GOOGLE_CLIENT_ID", "").strip()}


@app.get("/health", response_model=schemas.Health)
def health():
    """Liveness probe verifying server process responsiveness and database connectivity."""
    db.row("SELECT 1")
    return {"status": "ok"}


# Last: src/trainings.py takes Refused and current_user from here.
import trainings  # noqa: E402

app.include_router(trainings.router)
