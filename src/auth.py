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
MAX_FAILURES = 5  # failed logins per email, or sign-ups with a wrong invite code per IP ...
FAILURE_WINDOW = 15 * 60  # ... within this many seconds

load_dotenv()
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


# In memory, so it resets when the server restarts; enough for one dev server. Keyed by the
# email for a login and by ("signup", ip) for a sign-up, so the two never share a count.
_failures = defaultdict(deque)
_lock = threading.Lock()


def _recent(key, now):
    attempts = _failures[key]
    while attempts and attempts[0] <= now - FAILURE_WINDOW:
        attempts.popleft()
    return attempts


def seconds_locked(key):
    """Seconds until key may try again, or 0 if it has failed fewer than MAX_FAILURES times."""
    now = time.time()
    with _lock:
        attempts = _recent(key, now)
        return int(attempts[0] + FAILURE_WINDOW - now) + 1 if len(attempts) >= MAX_FAILURES else 0


def record_failure(key):
    with _lock:
        _recent(key, time.time()).append(time.time())


def clear_failures(key):
    with _lock:
        _failures.pop(key, None)
