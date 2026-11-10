import logging
import os
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

import audio
import db
import gnani_mock
import log

TIMEOUT = 15  # seconds per attempt
DEFAULT_CALL_LIMIT = 4000  # sent (not cached) calls by everyone, unless GNANI_CALL_LIMIT in .env says otherwise
# Sent calls one user may make in a rolling 24 hours, per quota: (setting in .env, default).
# stt: Prisma for Speak and training checks; enroll: Prisma for recording phrases while teaching
# Sunn; tts: Timbre, speaking and voice cloning.
LIMITS = {"stt": ("STT_DAILY_LIMIT", 20), "tts": ("TTS_DAILY_LIMIT", 20), "enroll": ("ENROLL_DAILY_LIMIT", 40)}
WINDOW = timedelta(hours=24)


class GnaniError(Exception):
    """A Gnani call that didn't give a result. code is what the frontend words:
    gnani_unreachable (no answer, or a server error twice), gnani_rejected (Gnani refused the
    request), credit_limit_reached (GNANI_CALL_LIMIT is used up) or daily_limit (this user's
    limit for one quota is used up; extra has kind, limit, used and resets_at)."""

    def __init__(self, code, detail, status=502, **extra):
        super().__init__(detail)
        self.code, self.detail, self.status, self.extra = code, detail, status, extra


def call_limit():
    load_dotenv()
    return int(os.environ.get("GNANI_CALL_LIMIT", DEFAULT_CALL_LIMIT))


def daily_limit(quota):
    name, default = LIMITS[quota]
    return int(os.environ.get(name, default))


def exempt_emails():
    """LIMIT_EXEMPT_EMAILS (comma separated), else OWNER_EMAIL: accounts no daily limit applies to."""
    emails = os.environ.get("LIMIT_EXEMPT_EMAILS", "").strip() or os.environ.get("OWNER_EMAIL", "")
    return {email.strip().lower() for email in emails.split(",") if email.strip()}


def stamp(moment):
    return moment.isoformat(timespec="seconds")


def quota_state(row, user_id, quota):
    """{used, limit, resets_at} for one quota over the last 24 hours; resets_at is when the oldest
    of those calls stops counting. row runs a query and returns its one row."""
    found = row("SELECT COUNT(*) AS n, MIN(created_at) AS oldest FROM api_calls"
                " WHERE user_id = ? AND quota = ? AND created_at > ?",
                (user_id, quota, stamp(datetime.now(timezone.utc) - WINDOW)))
    oldest = found["oldest"] and stamp(datetime.fromisoformat(found["oldest"]) + WINDOW)
    return {"used": found["n"], "limit": daily_limit(quota), "resets_at": oldest}


def usage(user_id):
    """The user's state for every quota, for GET /me/usage."""
    return {quota: quota_state(db.row, user_id, quota) for quota in LIMITS}


def reserve(kind, audio_seconds, user_id, quota):
    """Check GNANI_CALL_LIMIT and, when quota is given, the user's daily limit for it, then record
    the call as sent: all in one locked transaction, so two requests can't both take the last one.
    Returns the new api_calls id."""
    with db.locked() as conn:
        def row(sql, params=()):
            return conn.execute(sql, params).fetchone()

        limit = call_limit()
        if row("SELECT COUNT(*) AS n FROM api_calls WHERE cached = 0")["n"] >= limit:
            log.event("gnani_limit_reached", level=logging.WARNING, kind=kind, limit=limit)
            raise GnaniError("credit_limit_reached", f"the Gnani call limit ({limit}) is used up", status=429)
        user = row("SELECT email FROM users WHERE id = ?", (user_id,)) if quota else None
        if user and user["email"] not in exempt_emails():
            state = quota_state(row, user_id, quota)
            if state["used"] >= state["limit"]:
                log.event("daily_limit", level=logging.WARNING, kind=quota, user_id=user_id, limit=state["limit"])
                raise GnaniError("daily_limit", f"this account's {state['limit']} {quota} calls for the last 24 hours"
                                 " are used up", status=429, kind=quota, **state)
        return conn.execute("INSERT INTO api_calls (kind, cached, audio_seconds, created_at, user_id, quota)"
                            " VALUES (?, 0, ?, ?, ?, ?)",
                            (kind, audio_seconds, stamp(datetime.now(timezone.utc)), user_id, quota)).lastrowid


def check_startup():
    """Refuse to start in real mode (GNANI_MOCK off) when neither STT nor TTS key is configured."""
    load_dotenv()
    if not gnani_mock.on():
        stt_key = os.environ.get("GNANI_STT_API_KEY", "").strip()
        tts_key = os.environ.get("GNANI_TTS_API_KEY", "").strip()
        stt_valid = stt_key not in ("", "your-key-here", "your-stt-key-here")
        tts_valid = tts_key not in ("", "your-key-here", "your-tts-key-here")
        if not stt_valid and not tts_valid:
            raise RuntimeError("Neither GNANI_STT_API_KEY nor GNANI_TTS_API_KEY is configured in .env (see .env.example);"
                               " set GNANI_MOCK=1 to test without Gnani")


def record_cached(kind, audio_seconds, user_id=None):
    """A request answered from the cache: counted, but against no limit."""
    db.execute("INSERT INTO api_calls (kind, cached, audio_seconds, created_at, user_id) VALUES (?, 1, ?, ?, ?)",
               (kind, audio_seconds, stamp(datetime.now(timezone.utc)), user_id))
    log.event("gnani_call", kind=kind, cached=True)


def mask_secrets(text: str) -> str:
    if not isinstance(text, str):
        return text
    for key_var in ("GNANI_STT_API_KEY", "GNANI_TTS_API_KEY", "GROQ_API_KEY", "JWT_SECRET"):
        val = os.environ.get(key_var, "").strip()
        if val and val not in ("your-key-here", "your-stt-key-here", "your-tts-key-here", "your-groq-key-here", "placeholder"):
            text = text.replace(val, "[REDACTED]")
    return text


def reason(response):
    """Gnani's own error message: the docs' error body is {"success": false, "error": {"type", "message"}}."""
    try:
        error = response.json().get("error")
    except (ValueError, AttributeError):
        return mask_secrets(response.text[:200])
    msg = error.get("message", "") if isinstance(error, dict) else str(error or "")[:200]
    return mask_secrets(msg)


def post(kind, url, audio_seconds=None, user_id=None, quota=None, **request):
    """POST to Gnani (kind is stt, tts or clone) and return the 2xx response. Waits TIMEOUT
    seconds and retries once after a timeout, a lost connection or a 5xx. Every attempt is a
    sent call in api_calls; a TTS call's audio_seconds is the length of the audio it returned.
    A call for a user (user_id) counts once against their daily limit for quota (see LIMITS);
    a retry doesn't. Scripts pass no user."""
    load_dotenv()
    if gnani_mock.on():  # prisma.py and speak.py answer mock calls before they get here
        raise GnaniError("gnani_rejected", "GNANI_MOCK is on; no request is sent to Gnani")

    if kind == "stt":
        api_key = os.environ.get("GNANI_STT_API_KEY", "").strip()
        if not api_key or api_key in ("your-key-here", "your-stt-key-here"):
            raise GnaniError("gnani_unreachable", "GNANI_STT_API_KEY is not configured in .env", status=502)
    elif kind in ("tts", "clone"):
        api_key = os.environ.get("GNANI_TTS_API_KEY", "").strip()
        if not api_key or api_key in ("your-key-here", "your-tts-key-here"):
            raise GnaniError("gnani_unreachable", "GNANI_TTS_API_KEY is not configured in .env", status=502)
    else:
        raise GnaniError("gnani_unreachable", f"Unknown Gnani service kind: {kind}", status=502)

    headers = {"X-API-Key-ID": api_key}
    for attempt in (1, 2):
        call_id = reserve(kind, audio_seconds, user_id, quota if attempt == 1 else None)
        started = time.monotonic()
        try:
            response = requests.post(url, headers=headers, timeout=TIMEOUT, **request)
            failure = f"HTTP {response.status_code}" if response.status_code >= 500 else None
        except (requests.Timeout, requests.ConnectionError) as e:
            response, failure = None, type(e).__name__
        if kind == "tts" and failure is None and response.ok:
            db.execute("UPDATE api_calls SET audio_seconds = ? WHERE id = ?", (audio.seconds(response.content), call_id))
        log.event("gnani_call", kind=kind, cached=False, attempt=attempt, failure=failure,
                  status=None if response is None else response.status_code,
                  ms=round(1000 * (time.monotonic() - started)))
        if failure is None:
            break
    else:
        raise GnaniError("gnani_unreachable", f"the Gnani {kind} service did not answer ({failure})")
    if not response.ok:
        if response.status_code in (401, 403):
            raise GnaniError("gnani_rejected", f"Gnani {kind} authentication failed ({response.status_code}): {reason(response)}", status=502)
        if response.status_code == 429:
            raise GnaniError("credit_limit_reached", f"Gnani {kind} rate limit or quota reached (429): {reason(response)}", status=429)
        raise GnaniError("gnani_rejected", f"Gnani refused the {kind} request ({response.status_code}): {reason(response)}")
    return response
