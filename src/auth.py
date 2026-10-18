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
    """password_hash is None for an unknown email: it still runs a full verify, then fails."""
    try:
        hasher.verify(password_hash or DUMMY_HASH, password)
    except VerificationError:
        return False
    return password_hash is not None


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


# In memory, so it resets when the server restarts; enough for one dev server.
_failures = defaultdict(deque)
_lock = threading.Lock()


def _recent(email, now):
    attempts = _failures[email]
    while attempts and attempts[0] <= now - FAILURE_WINDOW:
        attempts.popleft()
    return attempts


def seconds_locked(email):
    """Seconds until email may try again, or 0 if it has failed fewer than MAX_FAILURES times."""
    now = time.time()
    with _lock:
        attempts = _recent(email, now)
        return int(attempts[0] + FAILURE_WINDOW - now) + 1 if len(attempts) >= MAX_FAILURES else 0


def record_failure(email):
    with _lock:
        _recent(email, time.time()).append(time.time())


def clear_failures(email):
    with _lock:
        _failures.pop(email, None)
