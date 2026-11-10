import os
import threading
import time
from collections import defaultdict, deque

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from dotenv import load_dotenv

COOKIE = "sunn_session"
SESSION_SECONDS = 30 * 24 * 3600
MIN_PASSWORD = 8
MAX_FAILURES = 5  # failed logins per email ...
FAILURE_WINDOW = 15 * 60  # ... within this many seconds
SIGNUP_WINDOW = 3600  # new accounts per IP within this many seconds: SIGNUPS_PER_IP_PER_HOUR

load_dotenv()
MAX_SIGNUPS = int(os.environ.get("SIGNUPS_PER_IP_PER_HOUR") or 5)
SECRET = os.environ.get("JWT_SECRET")
if not SECRET:
    raise RuntimeError("JWT_SECRET is not set; add one to .env (see .env.example)")

hasher = PasswordHasher()
# Checked when the email is unknown, so a wrong email takes as long as a wrong password.
DUMMY_HASH = hasher.hash("not a real password")


def hash_password(password):
    return hasher.hash(password)


def check_password(password_hash, password):
    """password_hash is None (or oauth:...) for an unknown email or oauth user: runs a full verify, then fails."""
    is_valid_hash = bool(password_hash and not password_hash.startswith("oauth:"))
    try:
        hasher.verify(password_hash if is_valid_hash else DUMMY_HASH, password)
    except Exception:
        return False
    return is_valid_hash


def make_token(user_id):
    issued = int(time.time())
    return jwt.encode({"sub": str(user_id), "iat": issued, "exp": issued + SESSION_SECONDS}, SECRET,
                      algorithm="HS256")


def user_id_from_token(token):
    """The user id in a valid, unexpired session token, else None."""
    try:
        return int(jwt.decode(token, SECRET, algorithms=["HS256"])["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def set_session(response, user_id):
    response.set_cookie(COOKIE, make_token(user_id), max_age=SESSION_SECONDS, httponly=True, secure=True,
                        samesite="lax", path="/")


def clear_session(response):
    response.delete_cookie(COOKIE, httponly=True, secure=True, samesite="lax", path="/")


# In memory, so it resets when the server restarts; enough for one server. Keyed by the
# email for failed logins and by ("signup", ip) for new accounts, so the two never share a count.
_failures = defaultdict(deque)
_lock = threading.Lock()


def _recent(key, now, window):
    attempts = _failures[key]
    while attempts and attempts[0] <= now - window:
        attempts.popleft()
    return attempts


def seconds_locked(key, limit=MAX_FAILURES, window=FAILURE_WINDOW):
    """Seconds until key may try again, or 0 if it has fewer than limit attempts in the last window seconds."""
    now = time.time()
    with _lock:
        attempts = _recent(key, now, window)
        return int(attempts[0] + window - now) + 1 if len(attempts) >= limit else 0


def record_failure(key):
    """Count one attempt for key: a failed login, or a new account from an IP."""
    with _lock:
        _failures[key].append(time.time())


def clear_failures(key):
    with _lock:
        _failures.pop(key, None)
