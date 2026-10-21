import uuid

CODE = "sunrise-42"


def signup(client, **extra):
    return client.post("/auth/signup", json={
        "name": "Asha", "email": f"{uuid.uuid4().hex[:8]}@example.com", "password": "password123",
        "language": "hi", "consent": True, **extra})


def test_without_an_invite_code_sign_up_is_open(env, monkeypatch):
    client = env.client()
    assert client.get("/config").json() == {"invite_required": False}
    assert signup(client).status_code == 200
    assert signup(env.client(), invite_code="anything").status_code == 200  # ignored
    monkeypatch.setenv("DEMO_INVITE_CODE", "  ")
    assert client.get("/config").json() == {"invite_required": False}
    assert signup(env.client()).status_code == 200


def test_with_an_invite_code_sign_up_needs_it(env, monkeypatch):
    monkeypatch.setenv("DEMO_INVITE_CODE", CODE)
    client = env.client()
    assert client.get("/config").json() == {"invite_required": True}
    for extra in ({}, {"invite_code": None}, {"invite_code": "sunrise-41"}, {"invite_code": "सूरज"}):
        refused = signup(client, **extra)
        assert refused.status_code == 403 and refused.json()["error"] == "invite_required", extra
    assert client.get("/auth/me").status_code == 401  # no account, no session
    user = signup(client, invite_code=CODE)
    assert user.status_code == 200 and client.get("/auth/me").json()["id"] == user.json()["id"]


def test_wrong_invite_codes_lock_sign_up_for_that_ip(env, monkeypatch):
    monkeypatch.setenv("DEMO_INVITE_CODE", CODE)
    client = env.client()
    for _ in range(5):
        assert signup(client, invite_code="guess").status_code == 403
    locked = signup(client, invite_code=CODE)
    assert locked.status_code == 429 and locked.json()["error"] == "too_many_attempts"
    assert 0 < locked.json()["retry_after"] <= 15 * 60
    # Login keeps its own count: the sign-up lockout doesn't touch it.
    assert client.post("/auth/login", json={"email": "a@example.com", "password": "x"}).json()["error"] == "bad_login"
