import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

PATH = "logs/app.log"

_logger = logging.getLogger("sunn")
_logger.setLevel(logging.INFO)
_logger.propagate = False


def event(name, level=logging.INFO, **fields):
    """Append one JSON line to logs/app.log. Callers pass ids, counts and codes only: never
    audio, phrase text, transcripts, emails, passwords or tokens."""
    if not _logger.handlers:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        _logger.addHandler(RotatingFileHandler(PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8"))
    line = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": logging.getLevelName(level), "event": name, **fields}
    _logger.log(level, json.dumps(line, ensure_ascii=False))
