"""Automated final QA assertions verifying environment placeholders, data safety,
and submission readiness contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_env_example_has_only_safe_placeholders():
    """Verify .env.example contains only non-secret placeholders and safe defaults."""
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    lines = [line.strip() for line in env_example.splitlines() if line.strip() and not line.startswith("#")]
    parsed = dict(line.split("=", 1) for line in lines)

    # Required environment keys must exist
    assert "GNANI_API_KEY" in parsed
    assert "JWT_SECRET" in parsed
    assert "GNANI_CALL_LIMIT" in parsed
    assert "OWNER_EMAIL" in parsed
    assert "DAILY_CALL_CAP_PER_USER" in parsed
    assert "DATA_DIR" in parsed
    assert "TRUST_PROXY" in parsed

    # Sensitive values must contain only placeholders
    assert parsed["GNANI_API_KEY"] == "your-key-here"
    assert parsed["JWT_SECRET"] == "generate-one-with-the-command-above"
    assert parsed["OWNER_EMAIL"] == "you@example.com"
    assert parsed["DEMO_INVITE_CODE"] == ""
    assert parsed["TRUST_PROXY"] == "0"


def test_gitignore_protects_local_data_and_secrets():
    """.gitignore must protect secrets, local data directories, and generated artifacts."""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    ignored_patterns = {line.strip() for line in gitignore.splitlines() if line.strip() and not line.startswith("#")}

    assert ".env" in ignored_patterns
    assert ".venv/" in ignored_patterns
    assert "data/*" in ignored_patterns
    assert "!data/default_phrases_*.txt" in ignored_patterns
    assert "logs/" in ignored_patterns
    assert "web/node_modules/" in ignored_patterns
    assert "web/dist/" in ignored_patterns
    assert "web/certs/" in ignored_patterns


def test_end_to_end_demo_user_journey(env):
    """Verify complete user demo lifecycle: signup, settings, recognize, confirm, stats, delete."""
    client = env.client()

    # 1. Signup with explicit consent
    signup_res = client.post("/auth/signup", json={
        "name": "Demo Presenter",
        "email": "presenter@example.com",
        "password": "password123",
        "language": "hi",
        "consent": True,
    })
    assert signup_res.status_code == 200
    user_data = signup_res.json()
    assert user_data["name"] == "Demo Presenter"
    assert user_data["language"] == "hi"

    # 2. Seed and verify default phrase bank
    seed_res = client.post("/me/phrases/default")
    assert seed_res.status_code == 200
    phrases = client.get("/me/phrases").json()
    assert len(phrases) >= 30, f"Expected 30+ default phrases, got {len(phrases)}"

    # 3. Update settings (caregiver name & phone)
    patch_res = client.patch("/me", json={
        "caregiver_name": "Family Helper",
        "caregiver_phone": "919876543210",
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["caregiver_name"] == "Family Helper"

    # 4. Enroll phrase and perform speech recognition with context
    env.enroll_phrase(client, "पानी चाहिए")
    rec = env.recognize(client, "पानी चाहिए", context="home")
    assert rec["candidates"], "Expected recognition candidates"
    assert rec["hypothesis"] == "पानी चाहिए"
    top_cand = rec["candidates"][0]

    # 5. Confirm recognition result
    conf_res = client.post("/me/confirm", json={
        "sample_id": rec["sample_id"],
        "phrase_id": top_cand["phrase_id"],
    })
    assert conf_res.status_code == 200
    assert conf_res.json()["phrase_id"] == top_cand["phrase_id"]

    # 6. Verify stats tracking
    stats_data = client.get("/me/stats").json()
    assert stats_data["confirmed"] >= 1
    assert any(p["phrase_id"] == top_cand["phrase_id"] for p in stats_data["top_phrases"])

    # 7. Complete forget-me account deletion
    del_res = client.delete("/me")
    assert del_res.status_code == 200
    assert del_res.json() == {"ok": True}

    # 8. Post-deletion authentication rejection
    assert client.get("/auth/me").status_code == 401


def test_speech_synthesis_and_recognition_error_contracts(env):
    """Verify TTS and recognition error handling contracts and fallback requirements."""
    client = env.signup("hi")

    # 1. Valid TTS audio response
    speak_res = client.post("/speak", json={"text": "पानी चाहिए"})
    assert speak_res.status_code == 200
    assert speak_res.headers["content-type"] == "audio/wav"
    assert len(speak_res.content) > 0

    # 2. Empty text input contract rejected cleanly with 400 invalid_input
    empty_speak_res = client.post("/speak", json={"text": "   "})
    assert empty_speak_res.status_code == 400
    assert empty_speak_res.json()["error"] == "invalid_input"

    # 3. Recognition endpoint requires authentication
    unauthed_client = env.client()
    unauthed_rec = unauthed_client.post("/me/recognize")
    assert unauthed_rec.status_code == 401

    # 4. Recognition without audio payload returns validation error (422)
    missing_audio_res = client.post("/me/recognize")
    assert missing_audio_res.status_code == 422

    # 5. Verify frontend api.js provides fallback to window.speechSynthesis
    api_code = (ROOT / "web" / "src" / "api.js").read_text(encoding="utf-8")
    assert "speakBrowserFallback" in api_code
    assert "window.speechSynthesis" in api_code
    assert "options.fallback" in api_code
