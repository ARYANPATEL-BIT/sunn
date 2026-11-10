"""Anyone can make an account, by email or Google; only the count per IP is limited."""
import uuid
from collections import deque
from unittest.mock import MagicMock, patch

import auth
import db


def signup(client, ip=None, **extra):
    headers = {"X-Forwarded-For": ip} if ip else {}
    return client.post("/auth/signup", headers=headers, json={
        "name": "Asha", "email": f"{uuid.uuid4().hex[:8]}@example.com", "password": "password123",
        "language": "hi", "consent": True, **extra})


def google(client, email, sub="google-sub-1", ip=None, **body):
    """POST /auth/google with an ID token Google says belongs to email."""
    answer = MagicMock(status_code=200)
    answer.json.return_value = {"iss": "https://accounts.google.com", "sub": sub, "email": email,
                                "email_verified": "true", "name": "Asha"}
    headers = {"X-Forwarded-For": ip} if ip else {}
    with patch("requests.get", return_value=answer):
        return client.post("/auth/google", headers=headers, json={"id_token": "token", **body})


def test_email_sign_up_needs_no_code(env):
    client = env.client()
    user = signup(client)
    assert user.status_code == 200, user.text
    assert client.get("/auth/me").json()["id"] == user.json()["id"]
    assert client.get("/config").status_code == 404  # it only ever said whether a code was needed


def test_google_sign_in_makes_the_account_when_there_is_none(env):
    first = google(env.client(), "new@example.com", language="ta", consent=True)
    assert first.status_code == 200, first.text
    assert first.json()["email"] == "new@example.com" and first.json()["language"] == "ta"
    again = google(env.client(), "new@example.com")
    assert again.status_code == 200 and again.json()["id"] == first.json()["id"]
    assert db.row("SELECT COUNT(*) AS n FROM users")["n"] == 1


def test_an_existing_user_signs_in(env):
    email = "asha@example.com"
    made = signup(env.client(), email=email).json()
    login = env.client().post("/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200 and login.json()["id"] == made["id"]
    with_google = google(env.client(), email)  # the same email through Google: the same account
    assert with_google.status_code == 200 and with_google.json()["id"] == made["id"]
    assert db.row("SELECT google_id FROM users WHERE id = ?", (made["id"],))["google_id"] == "google-sub-1"


def test_an_unknown_email_is_told_apart_from_a_wrong_password(env):
    signup(env.client(), email="asha@example.com")
    client = env.client()
    unknown = client.post("/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert unknown.status_code == 401 and unknown.json()["error"] == "no_account"
    wrong = client.post("/auth/login", json={"email": "asha@example.com", "password": "not-the-password"})
    assert wrong.status_code == 401 and wrong.json()["error"] == "bad_login"


def test_the_sixth_sign_up_from_one_ip_within_an_hour_is_refused(env, monkeypatch):
    monkeypatch.setenv("TRUST_PROXY", "1")
    for _ in range(5):
        assert signup(env.client(), "203.0.113.9").status_code == 200
    sixth = signup(env.client(), "203.0.113.9")
    assert sixth.status_code == 429 and sixth.json()["error"] == "too_many_attempts"
    assert 3500 < sixth.json()["retry_after"] <= 3601
    assert google(env.client(), "new@example.com", ip="203.0.113.9").status_code == 429  # Google counts too
    assert signup(env.client(), "198.51.100.7").status_code == 200  # another address has its own count

    key = ("signup", "203.0.113.9")
    auth._failures[key] = deque(at - 3601 for at in auth._failures[key])  # an hour later
    assert signup(env.client(), "203.0.113.9").status_code == 200
