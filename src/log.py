import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

PATH = "logs/app.log"
REDACTED = "[REDACTED]"
SENSITIVE_FIELD_NAMES = {
    "password", "password_hash", "token", "secret", "sunn_session",
    "jwt", "email", "audio", "audio_path", "transcript", "hypothesis",
    "prisma_hypothesis", "text", "caregiver_phone"
}

_logger = logging.getLogger("sunn")
_logger.setLevel(logging.INFO)
_logger.propagate = False


def sanitize_fields(fields):
    """Strip or redact sensitive fields so PII never enters logs/app.log."""
    clean = {}
    for k, v in fields.items():
        key_lower = k.lower()
        if any(sensitive in key_lower for sensitive in SENSITIVE_FIELD_NAMES):
            clean[k] = REDACTED
        else:
            clean[k] = v
    return clean


def event(name, level=logging.INFO, **fields):
    """Append one JSON line to logs/app.log. Callers pass ids, counts and codes only: never
    audio, phrase text, transcripts, emails, passwords or tokens."""
    if not _logger.handlers:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        _logger.addHandler(RotatingFileHandler(PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8"))
    sanitized = sanitize_fields(fields)
    line = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": logging.getLevelName(level), "event": name, **sanitized}
    _logger.log(level, json.dumps(line, ensure_ascii=False))
