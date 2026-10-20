import logging
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

import audio
import db
import log

TIMEOUT = 15  # seconds per attempt
DEFAULT_CALL_LIMIT = 4000  # sent (not cached) calls, unless GNANI_CALL_LIMIT in .env says otherwise


class GnaniError(Exception):
    """A Gnani call that didn't give a result. code is what the frontend words:
    gnani_unreachable (no answer, or a server error twice), gnani_rejected (Gnani refused the
    request) or credit_limit_reached (GNANI_CALL_LIMIT is used up)."""

    def __init__(self, code, detail, status=502):
        super().__init__(detail)
        self.code, self.detail, self.status = code, detail, status


def call_limit():
    load_dotenv()
    return int(os.environ.get("GNANI_CALL_LIMIT", DEFAULT_CALL_LIMIT))


def record(kind, cached, audio_seconds):
    db.execute("INSERT INTO api_calls (kind, cached, audio_seconds, created_at) VALUES (?, ?, ?, ?)",
               (kind, int(cached), audio_seconds, datetime.now(timezone.utc).isoformat(timespec="seconds")))
    if cached:
        log.event("gnani_call", kind=kind, cached=True)


def reason(response):
    """Gnani's own error message: the docs' error body is {"success": false, "error": {"type", "message"}}."""
    try:
        error = response.json().get("error")
    except (ValueError, AttributeError):
        return response.text[:200]
    return error.get("message", "") if isinstance(error, dict) else str(error or "")[:200]


def post(kind, url, audio_seconds=None, **request):
    """POST to Gnani (kind is stt, tts or clone) and return the 2xx response. Waits TIMEOUT
    seconds and retries once after a timeout, a lost connection or a 5xx. Every attempt is a
    sent call in api_calls; a TTS call's audio_seconds is the length of the audio it returned."""
    limit = call_limit()
    if db.row("SELECT COUNT(*) AS n FROM api_calls WHERE cached = 0")["n"] >= limit:
        log.event("gnani_limit_reached", level=logging.WARNING, kind=kind, limit=limit)
        raise GnaniError("credit_limit_reached", f"the Gnani call limit ({limit}) is used up", status=429)

    load_dotenv()
    headers = {"X-API-Key-ID": os.environ["GNANI_API_KEY"]}
    for attempt in (1, 2):
        started = time.monotonic()
        try:
            response = requests.post(url, headers=headers, timeout=TIMEOUT, **request)
            failure = f"HTTP {response.status_code}" if response.status_code >= 500 else None
        except (requests.Timeout, requests.ConnectionError) as e:
            response, failure = None, type(e).__name__
        if kind == "tts" and failure is None and response.ok:
            audio_seconds = audio.seconds(response.content)
        record(kind, False, audio_seconds)
        log.event("gnani_call", kind=kind, cached=False, attempt=attempt, failure=failure,
                  status=None if response is None else response.status_code,
                  ms=round(1000 * (time.monotonic() - started)))
        if failure is None:
            break
    else:
        raise GnaniError("gnani_unreachable", f"the Gnani {kind} service did not answer ({failure})")
    if not response.ok:
        raise GnaniError("gnani_rejected", f"Gnani refused the {kind} request ({response.status_code}): {reason(response)}")
    return response
