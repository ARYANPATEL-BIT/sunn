import hmac
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
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, FastAPI, File, Form, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException

import audio
import auth
import db
import gnani
import gnani_mock
import log
import matcher
import prisma
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
URGENT_PHRASES = {"मदद चाहिए", "दर्द हो रहा है", "I need help", "I'm in pain"}
# Building blocks every new user starts with. बेटे, not बेटा: the only person template takes को.
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
    return JSONResponse({"error": exc.code, "message": exc.detail}, status_code=exc.status)


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
            "has_own_voice": user["voice_embedding"] is not None, "use_own_voice": bool(user["use_own_voice"])}


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
    return phrase_out({key: owned("phrases", phrase_id, user_id)[key] for key in ("id", "text", "contexts", "urgent")})


def find_or_add_phrase(user_id, text, contexts="any", urgent=False):
    """Phrase id for text, reusing an identical phrase so one phrase never splits the bank."""
    text = clean_text(text)
    phrase = db.row("SELECT id FROM phrases WHERE user_id = ? AND text = ?", (user_id, text))
    if phrase:
        return phrase["id"]
    return db.execute("INSERT INTO phrases (user_id, text, contexts, urgent) VALUES (?, ?, ?, ?)",
                      (user_id, text, contexts, int(urgent)))


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


def save_and_transcribe(user, upload):
    """Store a phrase-length upload under data/users/<id>/; returns (path, Prisma hypothesis).
    Nothing is kept when Prisma fails or hears no speech."""
    wav = save_wav(upload, user_folder(user), PHRASE_SECONDS)
    try:
        hypothesis = prisma.transcribe(wav, user["language"], user["id"])
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
    path, hypothesis = save_and_transcribe(user, upload)
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
                  for slot, slot_words in DEFAULT_SLOT_WORDS[language].items() for word in slot_words
                  if (slot, word) not in words]
    statements += [("INSERT INTO templates (user_id, text, fixed_part) VALUES (?, ?, ?)",
                    (user_id, text, matcher.parse_template(text)[1]))
                   for text in DEFAULT_TEMPLATES[language] if text not in templates]
    if statements:
        db.transaction(*statements)


def trust_proxy():
    """TRUST_PROXY: on when the app runs behind a proxy that sets X-Forwarded-For (docs/DEPLOY.md)."""
    return os.environ.get("TRUST_PROXY", "").strip().lower() in ("1", "true", "yes", "on")


gnani_mock.check_startup(trust_proxy())  # never mock behind a proxy, and say so loudly when on


def client_ip(request):
    """The address sign-up attempts are counted by. Behind a proxy every request arrives from the
    proxy, so with TRUST_PROXY on it is the left-most X-Forwarded-For entry, the client as the
    proxy saw it; otherwise the socket's own peer."""
    if trust_proxy():
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else None


def invite_code():
    """DEMO_INVITE_CODE from .env; sign-up is open when it is unset or empty."""
    return os.environ.get("DEMO_INVITE_CODE", "").strip()


def check_invite(request, given):
    """Refuse a sign-up without the invite code, when there is one. Wrong codes count per IP, like
    failed logins per email, so the code can't be guessed."""
    code = invite_code()
    if not code:
        return
    attempts = ("signup", client_ip(request))
    wait = auth.seconds_locked(attempts)
    if wait:
        raise Refused(429, "too_many_attempts", "too many wrong invite codes, try again later", retry_after=wait)
    if not hmac.compare_digest((given or "").strip().encode("utf-8"), code.encode("utf-8")):
        auth.record_failure(attempts)
        raise Refused(403, "invite_required", "sign-up needs a valid invite code")


@app.post("/auth/signup", response_model=schemas.User)
def signup(body: schemas.Signup, request: Request, response: Response):
    name, email, password, language = body.name.strip(), body.email.strip().lower(), body.password, body.language
    check_invite(request, body.invite_code)
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
    add_default_building_blocks(user_id, language)
    auth.set_session(response, user_id)
    log.event("signup", user_id=user_id)
    return public(get_user(user_id))


@app.post("/auth/login", response_model=schemas.User)
def login(body: schemas.Login, response: Response):
    email, password = body.email.strip().lower(), body.password
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
    log.event("login", user_id=user["id"])
    return public(user)


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
    null or "" clears a caregiver field. language ("hi" or "en") is what new Prisma and Timbre
    calls use; nothing is deleted, but the matcher only uses samples in the current language."""
    updates = {}
    for field, value in changes.model_dump(exclude_unset=True).items():
        if field == "language" and value is not None:
            updates[field] = value
        elif field == "use_own_voice" and value is not None:
            if value and user["voice_embedding"] is None:
                raise Refused(409, "no_voice", "record your voice first")
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
    """Every phrase with its enrollment recordings (enrolled, so enrollment can resume), its
    samples in the user's current language (sample_count, confirmed recognitions included; the
    matcher ignores the rest), when it was last used, and sources: where its demo recordings came
    from (pilot, torgo, simulated; empty when every recording was made in the app)."""
    return [{**phrase_out(p), "sources": sorted(p["sources"].split(",")) if p["sources"] else []}
            for p in db.rows("""
        SELECT p.id, p.text, p.contexts, p.urgent,
            (SELECT COUNT(*) FROM samples s WHERE s.phrase_id = p.id AND s.source = 'enroll') AS enrolled,
            (SELECT COUNT(*) FROM samples s WHERE s.phrase_id = p.id AND s.language = :language) AS sample_count,
            (SELECT MAX(created_at) FROM uses u WHERE u.phrase_id = p.id) AS last_used_at,
            (SELECT GROUP_CONCAT(DISTINCT s.speech_source) FROM samples s WHERE s.phrase_id = p.id) AS sources
        FROM phrases p WHERE p.user_id = :u ORDER BY p.id""", {"u": user["id"], "language": user["language"]})]


@app.post("/me/phrases", response_model=schemas.Phrase)
def add_phrase(body: schemas.NewPhrase, user=Depends(current_user)):
    return get_phrase(user["id"], find_or_add_phrase(user["id"], body.text))


@app.post("/me/phrases/default", response_model=list[schemas.PhraseDetail])
def add_default_phrases(user=Depends(current_user)):
    """Add the everyday phrases in the user's language (data/default_phrases_<hi|en>.txt), with
    contexts from their group comment (GROUP_CONTEXTS; a group not listed there is any), and the
    default slot words and templates for it. Text the user already has is skipped, so after a
    language change this adds the new language's. One transaction for all of them: one commit
    instead of one per phrase, which kept sign-up waiting for seconds."""
    add_default_building_blocks(user["id"], user["language"])
    have = {p["text"] for p in db.rows("SELECT text FROM phrases WHERE user_id = ?", (user["id"],))}
    contexts, statements = "any", []
    with open(DEFAULT_PHRASES.format(language=user["language"]), encoding="utf-8") as f:
        for line in f:
            text = " ".join(line.split())
            if line.startswith("#"):
                contexts = GROUP_CONTEXTS.get(line.strip("# \n"), "any")
            elif text and text not in have:
                have.add(text)
                statements.append(("INSERT INTO phrases (user_id, text, contexts, urgent) VALUES (?, ?, ?, ?)",
                                   (user["id"], text, contexts, int(text in URGENT_PHRASES))))
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
            taken = db.row("SELECT id FROM phrases WHERE user_id = ? AND text = ? AND id != ?",
                           (user["id"], updates[field], phrase_id))
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
    """What a recording can be matched to: every phrase, and every template × slot word of its
    slot. Only samples in the user's current language are fingerprints: Prisma's hi-IN and
    en-IN hypotheses of the same speech aren't comparable. A composition's fingerprints are each slot word hypothesis joined to each fixed part
    hypothesis, in the template's word order. A composition whose text is already a phrase adds
    its fingerprints to that phrase instead of standing on its own."""
    user_id, heard = user["id"], defaultdict(list)
    for s in db.rows("SELECT phrase_id, slot_word_id, template_id, prisma_hypothesis FROM samples"
                     " WHERE user_id = ? AND source IS NOT NULL AND language = ?", (user_id, user["language"])):
        for column in ("phrase_id", "slot_word_id", "template_id"):
            if s[column] is not None:
                heard[column, s[column]].append(s["prisma_hypothesis"])

    candidates = {}
    for p in db.rows("SELECT id, text, contexts, urgent FROM phrases WHERE user_id = ?", (user_id,)):
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


@app.post("/me/recognize", response_model=schemas.Recognition)
def recognize(audio_file: UploadFile = File(alias="audio"), context: schemas.Context | None = Form(None),
              user=Depends(current_user)):
    """Top 3 candidates for a recording. Each has score = similarity + context + freq + time
    (see matcher.py) with those parts, urgent, and composed: a composed one is a template ×
    slot word that isn't a phrase yet, with its template_id and slot_word_id."""
    path, hypothesis = save_and_transcribe(user, audio_file)
    ranked = matcher.rank(hypothesis, candidates_for(user), context, priors_for(user["id"]))
    candidates = [{key: c[key] for key in ("phrase_id", "text", "score", "parts", "urgent", "composed",
                                           "template_id", "slot_word_id") if key in c} for c in ranked]
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
    phrase = get_phrase(user_id, find_or_add_phrase(user_id, new_text) if new_text is not None else phrase_id)
    db.transaction(("UPDATE samples SET phrase_id = ?, source = 'correction' WHERE id = ?", (phrase["id"], sample_id)),
                   ("INSERT INTO uses (user_id, phrase_id, created_at) VALUES (?, ?, ?)", (user_id, phrase["id"], now())))
    return {"sample_id": sample_id, "phrase_id": phrase["id"], "text": phrase["text"], "urgent": phrase["urgent"]}


@app.post("/speak", response_class=FileResponse, responses={200: {"content": {"audio/wav": {}}}})
def speak_text(body: schemas.Speak, user=Depends(current_user)):
    """Say text in the user's cloned voice when use_own_voice is on, else in the stock voice
    for their language. Answers audio/wav."""
    text = clean_text(body.text)
    if user["use_own_voice"] and user["voice_embedding"]:
        path = speak.synthesize(text, user["language"], json.loads(user["voice_embedding"]),
                                cache_dir=f"{voice_folder(user)}/tts", user_id=user["id"])
    else:
        path = speak.synthesize(text, user["language"], user_id=user["id"])
    return FileResponse(path, media_type="audio/wav")


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


@app.get("/me/usage", response_model=schemas.Usage)
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


@app.get("/config", response_model=schemas.Config)
def config():
    """What the app needs to know before anyone signs in."""
    return {"invite_required": bool(invite_code())}


@app.get("/health", response_model=schemas.Health)
def health():
    """Liveness probe verifying server process responsiveness and database connectivity."""
    db.row("SELECT 1")
    return {"status": "ok"}
