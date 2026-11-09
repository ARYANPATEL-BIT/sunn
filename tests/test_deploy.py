"""The single deployable app (src/server.py) and the client address behind a proxy."""
import os
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
    (dist / "assets" / "big.js").write_bytes(b"console.log('sunn');\n" * 500)  # bytes: no CRLF on Windows
    client = TestClient(server.make_app(str(dist)), base_url="https://testserver")

    for path in ("/", "/app/speak", "/login?next=/app/enroll"):
        page = client.get(path)
        assert page.status_code == 200 and page.text == "<p>sunn</p>", path
    assert client.get("/assets/app.js").text == "console.log('sunn')"
    big = client.get("/assets/big.js", headers={"Accept-Encoding": "gzip"})
    assert big.headers["content-encoding"] == "gzip" and big.text == "console.log('sunn');\n" * 500
    assert "content-encoding" not in client.get("/api/config", headers={"Accept-Encoding": "gzip"}).headers

    assert client.get("/api/config").json() == {"invite_required": False}
    missing = client.get("/api/nowhere")
    assert missing.status_code == 404 and missing.json()["error"] == "not_found"
    assert signup(client, path="/api/auth/signup").status_code == 200  # as the browser does
    assert client.get("/api/auth/me").status_code == 200  # the cookie comes back on /api paths


def test_health_check_endpoint_and_liveness(env, tmp_path):
    import server

    # 1. API health probe directly through client
    client = env.client()
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

    # 2. Server top-level and /api mounting health probes
    dist = tmp_path / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<p>sunn</p>")
    server_client = TestClient(server.make_app(str(dist)), base_url="https://testserver")

    root_health = server_client.get("/health")
    assert root_health.status_code == 200
    assert root_health.json() == {"status": "ok"}

    api_health = server_client.get("/api/health")
    assert api_health.status_code == 200
    assert api_health.json() == {"status": "ok"}

    # 3. Verify no sensitive data or diagnostic leak
    for key in ("secret", "key", "token", "env", "password", "path"):
        assert key not in root_health.text.lower()


def test_deploy_space_secret_and_blocked_path_validation(tmp_path):
    import sys
    from pathlib import Path

    scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import deploy_space

    # 1. Blocked vs allowed path rules
    candidate_files = [
        ".env",
        ".env.local",
        "data/app.db",
        "logs/app.log",
        "web/certs/cert.pem",
        ".env.example",
        "data/default_phrases_hi.txt",
        "src/api.py",
    ]
    blocked = deploy_space.blocked_paths(candidate_files)
    assert ".env" in blocked
    assert ".env.local" in blocked
    assert "data/app.db" in blocked
    assert "logs/app.log" in blocked
    assert "web/certs/cert.pem" in blocked
    assert ".env.example" not in blocked
    assert "data/default_phrases_hi.txt" not in blocked
    assert "src/api.py" not in blocked

    # 2. Secret leakage detection with real secret
    test_folder = tmp_path / "repo"
    test_folder.mkdir()
    (test_folder / "file_with_secret.py").write_text("API_KEY = 'real-secret-token-xyz'")
    (test_folder / "clean_file.py").write_text("API_KEY = 'your-key-here'")

    env_file = tmp_path / ".env"
    env_file.write_text("GNANI_STT_API_KEY=real-secret-token-xyz\nJWT_SECRET=generate-one-with-the-command-above")

    leaks = deploy_space.files_with_secrets(["file_with_secret.py", "clean_file.py"], test_folder, env_file)
    assert len(leaks) == 1
    assert "file_with_secret.py (GNANI_STT_API_KEY)" in leaks
    assert "clean_file.py" not in leaks[0]


def test_missing_or_placeholder_gnani_key_fails_safely(env, monkeypatch):
    """When GNANI_STT_API_KEY or GNANI_TTS_API_KEY is unset or set to placeholder, API answers 502 safely."""
    import gnani
    import pytest

    # 1. Test STT with placeholder and empty string
    monkeypatch.setenv("GNANI_STT_API_KEY", "your-stt-key-here")
    with pytest.raises(gnani.GnaniError) as exc_info:
        gnani.post("stt", "https://api.vachana.ai/stt/v3", data={}, files={})
    assert exc_info.value.status == 502
    assert exc_info.value.code == "gnani_unreachable"
    assert "GNANI_STT_API_KEY is not configured" in exc_info.value.detail

    monkeypatch.setenv("GNANI_STT_API_KEY", "")
    with pytest.raises(gnani.GnaniError) as exc_info2:
        gnani.post("stt", "https://api.vachana.ai/stt/v3", data={}, files={})
    assert exc_info2.value.status == 502
    assert "GNANI_STT_API_KEY is not configured" in exc_info2.value.detail

    # 2. Test TTS with placeholder and empty string
    monkeypatch.setenv("GNANI_TTS_API_KEY", "your-tts-key-here")
    with pytest.raises(gnani.GnaniError) as exc_info3:
        gnani.post("tts", "https://api.vachana.ai/test", user_id=1, json={"text": "test"})
    assert exc_info3.value.status == 502
    assert exc_info3.value.code == "gnani_unreachable"
    assert "GNANI_TTS_API_KEY is not configured" in exc_info3.value.detail

    monkeypatch.setenv("GNANI_TTS_API_KEY", "")
    with pytest.raises(gnani.GnaniError) as exc_info4:
        gnani.post("tts", "https://api.vachana.ai/test", user_id=1, json={"text": "test"})
    assert exc_info4.value.status == 502
    assert "GNANI_TTS_API_KEY is not configured" in exc_info4.value.detail


def test_database_custom_data_dir_and_persistence_isolation(tmp_path, monkeypatch):
    """Verify DATA_DIR configures database path, runs migrations, and handles user lifecycle."""
    custom_dir = tmp_path / "custom_data"
    monkeypatch.setenv("DATA_DIR", str(custom_dir))

    import db
    db.DATA_DIR = str(custom_dir)
    db.DB_PATH = str(custom_dir / "app.db")
    db.init()

    # 1. DB file created inside custom data dir
    assert (custom_dir / "app.db").exists()

    # 2. Tables and columns exist
    tables = [r["name"] for r in db.rows("SELECT name FROM sqlite_master WHERE type='table'")]
    for t in ("users", "phrases", "slot_words", "templates", "samples", "uses", "api_calls"):
        assert t in tables

    # 3. Insert and verify single-user deletion cascade
    uid = db.execute(
        "INSERT INTO users (name, email, password_hash, language, consent_given_at) VALUES (?, ?, ?, ?, ?)",
        ("Persist User", "persist@example.com", "hash", "en", "2026-10-22T00:00:00Z"),
    )
    pid = db.execute("INSERT INTO phrases (user_id, text) VALUES (?, ?)", (uid, "Help me"))
    db.execute("INSERT INTO uses (user_id, phrase_id, created_at) VALUES (?, ?, ?)", (uid, pid, "2026-10-22T00:00:00Z"))
    db.execute(
        "INSERT INTO api_calls (kind, cached, audio_seconds, created_at, user_id) VALUES (?, ?, ?, ?, ?)",
        ("tts", 0, 1.5, "2026-10-22T00:00:00Z", uid),
    )

    # Before deletion
    assert db.row("SELECT COUNT(*) AS c FROM phrases WHERE user_id = ?", (uid,))["c"] == 1
    assert db.row("SELECT user_id FROM api_calls WHERE user_id = ?", (uid,))["user_id"] == uid

    # Run delete_user
    db.delete_user(uid)
    assert db.row("SELECT COUNT(*) AS c FROM users WHERE id = ?", (uid,))["c"] == 0
    assert db.row("SELECT COUNT(*) AS c FROM phrases WHERE user_id = ?", (uid,))["c"] == 0
    assert db.row("SELECT COUNT(*) AS c FROM uses WHERE user_id = ?", (uid,))["c"] == 0
    # api_calls retained as anonymous counter with user_id NULL
    assert db.row("SELECT user_id FROM api_calls")["user_id"] is None


def test_static_hosting_path_traversal_protection(env, tmp_path):
    """Ensure path traversal attacks cannot escape web/dist to access secrets, databases, or logs."""
    import server

    # Setup sandbox: root directory containing secret file and a dist folder
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / ".env").write_text("SECRET_KEY=leaked_production_secret")
    (sandbox / "app.db").write_text("SQLITE_BINARY_DUMP_CONTENT")

    dist = sandbox / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>Sunn App</body></html>")
    (dist / "style.css").write_text("body { color: black; }")

    client = TestClient(server.make_app(str(dist)), base_url="https://testserver")

    # Valid static asset request
    assert client.get("/style.css").text == "body { color: black; }"

    # Traversal attempts must never return secret files or db content
    traversal_paths = [
        "/../.env",
        "/../../.env",
        "/..%2F..%2F.env",
        "/../app.db",
        "/../../app.db",
        "/..%2F..%2Fapp.db",
        "/..%2F.env",
        "/static/../../.env",
    ]
    for path in traversal_paths:
        res = client.get(path)
        assert "SECRET_KEY" not in res.text, f"Secret leaked via path {path}"
        assert "SQLITE_BINARY_DUMP_CONTENT" not in res.text, f"Database leaked via path {path}"
        assert res.status_code in (200, 404, 400)


def test_signup_invite_code_enforcement_and_frontend_contract(env, monkeypatch):
    """Verify signup invite code enforcement in API and frontend integration."""
    from pathlib import Path

    client = env.client()

    # 1. Open signup when DEMO_INVITE_CODE is unset
    monkeypatch.delenv("DEMO_INVITE_CODE", raising=False)
    assert client.get("/config").json() == {"invite_required": False}
    open_res = signup(client)
    assert open_res.status_code == 200

    # 2. Restricted signup when DEMO_INVITE_CODE is set
    monkeypatch.setenv("DEMO_INVITE_CODE", "secret-evaluator-pass")
    assert client.get("/config").json() == {"invite_required": True}

    # Missing invite code is rejected with 403
    rejected = signup(client)
    assert rejected.status_code == 403
    assert rejected.json()["error"] == "invite_required"

    # Valid invite code is accepted with 200
    allowed = signup(client, invite_code="secret-evaluator-pass")
    assert allowed.status_code == 200

    # 3. Verify frontend AuthPages and api client have invite code contract
    root = Path(__file__).resolve().parent.parent
    auth_pages_code = (root / "web" / "src" / "AuthPages.jsx").read_text(encoding="utf-8")
    api_js_code = (root / "web" / "src" / "api.js").read_text(encoding="utf-8")

    assert "inviteRequired" in auth_pages_code
    assert "signup-invite" in auth_pages_code
    assert "invite_code: inviteCode" in auth_pages_code
    assert "export const config =" in api_js_code


def test_deployment_dry_run_preflight_check():
    """Verify that deployment dry-run check passes on current HEAD with zero blocked files."""
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    cmd = [
        "uv",
        "run",
        "scripts/deploy_space.py",
        "--check-only",
    ]
    # Without conftest's fake secrets: test keys are in conftest.py itself, so the script would
    # flag them whenever .env doesn't set real keys.
    env = {k: v for k, v in os.environ.items() if k not in ("GNANI_STT_API_KEY", "GNANI_TTS_API_KEY", "GNANI_API_KEY", "JWT_SECRET", "GROQ_API_KEY", "LLM_API_KEY")}
    res = subprocess.run(cmd, cwd=root, capture_output=True, text=True, env=env)
    assert res.returncode == 0, f"deploy_space.py --check-only failed: {res.stdout}{res.stderr}"
    assert "checks passed:" in res.stdout
    assert "docs/SUBMISSION_PACKAGE.md" in res.stdout
    assert "data/app.db" not in res.stdout
    assert ".env" not in res.stdout.splitlines()
