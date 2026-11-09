"""Tests verifying environment variable separation, Groq AI configuration,
frontend credential isolation, and .env.example contract compliance."""
import os
from pathlib import Path
import pytest
import requests

import gnani
import llm_judge
import prisma
import speak
import trainings

ROOT = Path(__file__).resolve().parent.parent


class MockResponse:
    def __init__(self, status_code=200, json_data=None, content=b""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.content = content
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._json_data

    @property
    def text(self):
        return str(self._json_data)


# -----------------------------------------------------------------------------
# 1. Speech-to-Text (STT) Credential Isolation
# -----------------------------------------------------------------------------

def test_stt_client_reads_gnani_stt_api_key(monkeypatch):
    """STT operations must authenticate using GNANI_STT_API_KEY."""
    captured_headers = {}

    def mock_post(url, headers, timeout, **kwargs):
        captured_headers.update(headers)
        return MockResponse(200, {"success": True, "transcript": "नमस्ते"})

    monkeypatch.setattr(gnani.requests, "post", mock_post)
    monkeypatch.setenv("GNANI_STT_API_KEY", "real-mock-stt-key")
    monkeypatch.delenv("GNANI_TTS_API_KEY", raising=False)
    monkeypatch.delenv("GNANI_API_KEY", raising=False)
    monkeypatch.delenv("GNANI_MOCK", raising=False)

    resp = gnani.post("stt", prisma.URL, data={"language_code": "hi-IN"}, files={})
    assert resp.ok
    assert captured_headers.get("X-API-Key-ID") == "real-mock-stt-key"


def test_stt_missing_key_produces_actionable_error(monkeypatch):
    """Missing or placeholder GNANI_STT_API_KEY produces actionable error."""
    monkeypatch.delenv("GNANI_MOCK", raising=False)

    for placeholder in ("", "your-key-here", "your-stt-key-here"):
        monkeypatch.setenv("GNANI_STT_API_KEY", placeholder)
        with pytest.raises(gnani.GnaniError) as exc:
            gnani.post("stt", prisma.URL, data={}, files={})
        assert exc.value.status == 502
        assert exc.value.code == "gnani_unreachable"
        assert "GNANI_STT_API_KEY is not configured" in exc.value.detail


def test_stt_never_falls_back_to_tts_credentials(monkeypatch):
    """STT must never fall back to GNANI_TTS_API_KEY or generic credentials."""
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_STT_API_KEY", "")
    monkeypatch.setenv("GNANI_TTS_API_KEY", "valid-tts-key-that-stt-must-not-use")
    monkeypatch.setenv("GNANI_API_KEY", "legacy-generic-key")

    with pytest.raises(gnani.GnaniError) as exc:
        gnani.post("stt", prisma.URL, data={}, files={})
    assert exc.value.status == 502
    assert "GNANI_STT_API_KEY is not configured" in exc.value.detail


# -----------------------------------------------------------------------------
# 2. Text-to-Speech (TTS) Credential Isolation
# -----------------------------------------------------------------------------

def test_tts_client_reads_gnani_tts_api_key(monkeypatch):
    """TTS and voice clone operations must authenticate using GNANI_TTS_API_KEY."""
    captured_headers = {}

    def mock_post(url, headers, timeout, **kwargs):
        captured_headers.update(headers)
        return MockResponse(200, {"success": True}, content=b"RIFFdummywav")

    monkeypatch.setattr(gnani.requests, "post", mock_post)
    monkeypatch.setenv("GNANI_TTS_API_KEY", "real-mock-tts-key")
    monkeypatch.delenv("GNANI_STT_API_KEY", raising=False)
    monkeypatch.delenv("GNANI_API_KEY", raising=False)
    monkeypatch.delenv("GNANI_MOCK", raising=False)

    # 1. TTS synthesis endpoint
    resp = gnani.post("tts", speak.URL, json={"text": "परीक्षण"})
    assert resp.ok
    assert captured_headers.get("X-API-Key-ID") == "real-mock-tts-key"

    # 2. Voice clone endpoint
    captured_headers.clear()
    resp_clone = gnani.post("clone", speak.CLONE_URL, files={})
    assert resp_clone.ok
    assert captured_headers.get("X-API-Key-ID") == "real-mock-tts-key"


def test_tts_missing_key_produces_actionable_error(monkeypatch):
    """Missing or placeholder GNANI_TTS_API_KEY produces actionable error."""
    monkeypatch.delenv("GNANI_MOCK", raising=False)

    for placeholder in ("", "your-key-here", "your-tts-key-here"):
        monkeypatch.setenv("GNANI_TTS_API_KEY", placeholder)
        with pytest.raises(gnani.GnaniError) as exc:
            gnani.post("tts", speak.URL, json={"text": "test"})
        assert exc.value.status == 502
        assert exc.value.code == "gnani_unreachable"
        assert "GNANI_TTS_API_KEY is not configured" in exc.value.detail


def test_tts_never_falls_back_to_stt_credentials(monkeypatch):
    """TTS must never fall back to GNANI_STT_API_KEY or generic credentials."""
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_TTS_API_KEY", "")
    monkeypatch.setenv("GNANI_STT_API_KEY", "valid-stt-key-that-tts-must-not-use")
    monkeypatch.setenv("GNANI_API_KEY", "legacy-generic-key")

    with pytest.raises(gnani.GnaniError) as exc:
        gnani.post("tts", speak.URL, json={"text": "test"})
    assert exc.value.status == 502
    assert "GNANI_TTS_API_KEY is not configured" in exc.value.detail


def test_independent_service_availability(monkeypatch):
    """When only one service key is configured, the other service does not disable it."""
    captured = {}

    def mock_post(url, headers, timeout, **kwargs):
        captured["header"] = headers.get("X-API-Key-ID")
        return MockResponse(200, {"success": True, "transcript": "नमस्ते"})

    monkeypatch.setattr(gnani.requests, "post", mock_post)
    monkeypatch.delenv("GNANI_MOCK", raising=False)

    # STT configured, TTS unconfigured: STT succeeds while TTS fails gracefully
    monkeypatch.setenv("GNANI_STT_API_KEY", "stt-only-key")
    monkeypatch.setenv("GNANI_TTS_API_KEY", "")

    stt_resp = gnani.post("stt", prisma.URL, data={}, files={})
    assert stt_resp.ok
    assert captured["header"] == "stt-only-key"

    with pytest.raises(gnani.GnaniError) as exc:
        gnani.post("tts", speak.URL, json={"text": "test"})
    assert "GNANI_TTS_API_KEY is not configured" in exc.value.detail


# -----------------------------------------------------------------------------
# 3. Groq Cloud AI Assistant Configuration
# -----------------------------------------------------------------------------

def test_groq_reads_groq_api_key_and_defaults_to_gpt_oss_120b(monkeypatch):
    """Groq requests authenticate with GROQ_API_KEY and default to openai/gpt-oss-120b."""
    captured = {}

    class MockHttpxResponse:
        status_code = 200
        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": '{"choice": "1", "confidence": 0.95, "reason": "clear match"}'
                    }
                }]
            }
        def raise_for_status(self):
            pass

    def mock_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return MockHttpxResponse()

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setenv("GROQ_API_KEY", "real-mock-groq-key")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    candidates = [{"id": "1", "text": "पानी चाहिए"}]
    verdict = llm_judge.ask("baani chahiye", candidates, {"place": "home"})

    assert verdict is not None
    assert verdict["choice"] == "1"
    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer real-mock-groq-key"
    assert captured["json"]["model"] == "openai/gpt-oss-120b"


def test_groq_model_override_is_respected(monkeypatch):
    """Configuring GROQ_MODEL overrides the default model."""
    captured = {}

    class MockHttpxResponse:
        status_code = 200
        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": '{"choice": "1", "confidence": 0.9, "reason": "model test"}'
                    }
                }]
            }
        def raise_for_status(self):
            pass

    def mock_post(url, headers, json, timeout):
        captured["json"] = json
        return MockHttpxResponse()

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setenv("GROQ_API_KEY", "real-mock-groq-key")
    monkeypatch.setenv("GROQ_MODEL", "custom-groq-model-100b")

    candidates = [{"id": "1", "text": "पानी चाहिए"}]
    llm_judge.ask("baani", candidates, {})

    assert captured["json"]["model"] == "custom-groq-model-100b"


def test_groq_missing_key_handled_safely(monkeypatch):
    """When GROQ_API_KEY is missing, assistant returns None safely without raising."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    candidates = [{"id": "1", "text": "पानी चाहिए"}]
    verdict = llm_judge.ask("baani", candidates, {})
    assert verdict is None

    alt_result = trainings.call_groq_alternatives("पानी चाहिए", "hi", [])
    assert alt_result is None


# -----------------------------------------------------------------------------
# 4. Frontend Secret Exposure Audit
# -----------------------------------------------------------------------------

def test_no_secrets_exposed_in_public_config_routes(env):
    """Public config endpoints return only safe non-secret flags."""
    client = env.client()

    config_res = client.get("/config")
    assert config_res.status_code == 200
    config_keys = set(config_res.json().keys())
    assert config_keys == {"invite_required"}

    google_res = client.get("/auth/google/config")
    assert google_res.status_code == 200
    google_keys = set(google_res.json().keys())
    assert google_keys == {"client_id"}


# -----------------------------------------------------------------------------
# 5. .env.example Inventory and Placeholder Contract
# -----------------------------------------------------------------------------

def test_env_example_contains_all_inventoried_variables():
    """Verify root .env.example documents all active environment variables."""
    example_path = ROOT / ".env.example"
    assert example_path.exists(), ".env.example must exist at repository root"

    content = example_path.read_text(encoding="utf-8")
    parsed = {}
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            parsed[k.strip()] = v.strip()

    expected_vars = [
        "GNANI_STT_API_KEY",
        "GNANI_TTS_API_KEY",
        "GNANI_CALL_LIMIT",
        "DAILY_CALL_CAP_PER_USER",
        "TRAINING_CHECKS_PER_DAY",
        "WORD_CLEAR_THRESHOLD",
        "GNANI_MOCK",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "LLM_BASE_URL",
        "LLM_ENABLED",
        "LLM_REASONING_EFFORT",
        "LLM_MODE",
        "LLM_MARGIN",
        "LLM_MIN_SCORE",
        "LLM_TIMEOUT_S",
        "LLM_RATE_PER_MIN",
        "JWT_SECRET",
        "OWNER_EMAIL",
        "DEMO_INVITE_CODE",
        "GOOGLE_CLIENT_ID",
        "DATA_DIR",
        "TRUST_PROXY",
        "RERANKER_ENABLED",
        "RERANKER_WEIGHT",
        "RERANKER_PATH",
        "RERANKER_THREADS",
    ]

    for var in expected_vars:
        assert var in parsed, f"Variable {var} missing from .env.example"

    # Verify safe defaults and placeholders
    assert parsed["GNANI_STT_API_KEY"] == "your-stt-key-here"
    assert parsed["GNANI_TTS_API_KEY"] == "your-tts-key-here"
    assert parsed["GROQ_API_KEY"] == ""
    assert parsed["GROQ_MODEL"] == "openai/gpt-oss-120b"
    assert parsed["LLM_BASE_URL"] == "https://api.groq.com/openai/v1"
    assert parsed["JWT_SECRET"] == "generate-one-with-the-command-above"
