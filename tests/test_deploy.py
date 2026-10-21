"""The single deployable app (src/server.py) and the client address behind a proxy."""
import uuid

from fastapi.testclient import TestClient

CODE = "sunrise-42"


def signup(client, forwarded_for=None, path="/auth/signup", **extra):
    # A proxy appends its own hop, so the client is the left-most entry and the right one is shared.
    headers = {"X-Forwarded-For": f"{forwarded_for}, 10.0.0.1"} if forwarded_for else {}
    return client.post(path, headers=headers, json={
        "name": "Asha", "email": f"{uuid.uuid4().hex[:8]}@example.com", "password": "password123",
        "language": "hi", "consent": True, **extra})


def test_without_trust_proxy_forwarded_for_is_ignored(env, monkeypatch):
    monkeypatch.setenv("DEMO_INVITE_CODE", CODE)
    client = env.client()
    for n in range(5):
        assert signup(client, f"203.0.113.{n}", invite_code="guess").status_code == 403
    # All five counted against the connection's own address, whatever the header claimed.
    assert signup(client, "198.51.100.7", invite_code=CODE).status_code == 429


def test_behind_a_trusted_proxy_each_client_has_its_own_count(env, monkeypatch):
    monkeypatch.setenv("DEMO_INVITE_CODE", CODE)
    monkeypatch.setenv("TRUST_PROXY", "1")
    client = env.client()
    for _ in range(5):
        assert signup(client, "203.0.113.5", invite_code="guess").status_code == 403
    assert signup(client, "203.0.113.5", invite_code=CODE).status_code == 429
    assert signup(env.client(), "198.51.100.7", invite_code=CODE).status_code == 200  # someone else
    assert signup(env.client(), invite_code=CODE).status_code == 200  # no header: the connection's address


def test_one_app_serves_the_api_and_the_web_app(env, tmp_path):
    import server

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<p>sunn</p>")
    (dist / "assets" / "app.js").write_text("console.log('sunn')")
    client = TestClient(server.make_app(str(dist)), base_url="https://testserver")

    for path in ("/", "/app/speak", "/login?next=/app/enroll"):
        page = client.get(path)
        assert page.status_code == 200 and page.text == "<p>sunn</p>", path
    assert client.get("/assets/app.js").text == "console.log('sunn')"

    assert client.get("/api/config").json() == {"invite_required": False}
    missing = client.get("/api/nowhere")
    assert missing.status_code == 404 and missing.json()["error"] == "not_found"
    assert signup(client, path="/api/auth/signup").status_code == 200  # as the browser does
    assert client.get("/api/auth/me").status_code == 200  # the cookie comes back on /api paths
