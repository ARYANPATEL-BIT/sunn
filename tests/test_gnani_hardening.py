"""Unit and integration tests for Gnani STT and TTS hardening and error resilience.

All tests use mocked HTTP responses and synthetic waveforms; ZERO live API credits are consumed.
"""
import io
import os
from unittest.mock import MagicMock

import numpy as np
import pytest
import requests
import soundfile

import audio
import db
import gnani
import prisma
import speak


class MockHttpResponse:
    def __init__(self, status_code=200, json_data=None, content=b"", headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.content = content
        self.headers = headers or {}
        self.ok = 200 <= status_code < 300
        self.text = content.decode("utf-8", errors="ignore") if content else ""

    def json(self):
        if self._json_data is not None:
            return self._json_data
        raise ValueError("Invalid JSON response")


def make_test_wav_bytes(seconds=1.0, rate=16000) -> bytes:
    t = np.arange(int(seconds * rate)) / rate
    waveform = 0.2 * np.sin(2 * np.pi * 440.0 * t)
    buf = io.BytesIO()
    soundfile.write(buf, waveform, rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def isolate_gnani_cache(tmp_path, monkeypatch):
    """Ensure each test runs with an isolated cache directory."""
    monkeypatch.setattr(prisma, "CACHE_DIR", str(tmp_path / "cache_prisma"))
    monkeypatch.setattr(speak, "CACHE_DIR", str(tmp_path / "cache_tts"))



# =============================================================================
# STT Pipeline Hardening Tests
# =============================================================================

def test_stt_successful_response(tmp_path, monkeypatch):
    """Prisma STT parses valid JSON and caches the result."""
    wav_path = str(tmp_path / "test.wav")
    with open(wav_path, "wb") as f:
        f.write(make_test_wav_bytes(1.0))

    mock_resp = MockHttpResponse(200, json_data={"success": True, "transcript": "नमस्ते आज मौसम अच्छा है"})
    monkeypatch.setattr(gnani.requests, "post", lambda *a, **kw: mock_resp)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_STT_API_KEY", "mock-stt-key")

    transcript = prisma.transcribe(wav_path, language="hi")
    assert transcript == "नमस्ते आज मौसम अच्छा है"


def test_stt_invalid_authentication(tmp_path, monkeypatch):
    """Gnani HTTP 401/403 produces gnani_rejected without looping retries."""
    wav_path = str(tmp_path / "test.wav")
    with open(wav_path, "wb") as f:
        f.write(make_test_wav_bytes(1.0))

    call_count = 0

    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return MockHttpResponse(401, json_data={"success": False, "error": {"type": "AuthError", "message": "Invalid API key"}})

    monkeypatch.setattr(gnani.requests, "post", mock_post)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_STT_API_KEY", "invalid-key")

    with pytest.raises(gnani.GnaniError) as exc:
        prisma.transcribe(wav_path, language="hi")

    assert exc.value.code == "gnani_rejected"
    assert "401" in exc.value.detail
    assert call_count == 1  # Verify no retry on 401 client error


def test_stt_empty_transcript_handling(tmp_path, monkeypatch):
    """Empty string transcript from provider is returned cleanly for downstream validation."""
    wav_path = str(tmp_path / "test.wav")
    with open(wav_path, "wb") as f:
        f.write(make_test_wav_bytes(1.0))

    mock_resp = MockHttpResponse(200, json_data={"success": True, "transcript": ""})
    monkeypatch.setattr(gnani.requests, "post", lambda *a, **kw: mock_resp)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_STT_API_KEY", "mock-stt-key")

    transcript = prisma.transcribe(wav_path, language="hi")
    assert transcript == ""


def test_stt_provider_timeout_handled(tmp_path, monkeypatch):
    """Timeout during STT request produces actionable gnani_unreachable error."""
    wav_path = str(tmp_path / "test.wav")
    with open(wav_path, "wb") as f:
        f.write(make_test_wav_bytes(1.0))

    def mock_post(*args, **kwargs):
        raise requests.Timeout("Connection timed out")

    monkeypatch.setattr(gnani.requests, "post", mock_post)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_STT_API_KEY", "mock-stt-key")

    with pytest.raises(gnani.GnaniError) as exc:
        prisma.transcribe(wav_path, language="hi")

    assert exc.value.code == "gnani_unreachable"
    assert "service did not answer" in exc.value.detail


def test_stt_provider_500_server_error(tmp_path, monkeypatch):
    """Gnani 500 server error retries once then raises gnani_unreachable."""
    wav_path = str(tmp_path / "test.wav")
    with open(wav_path, "wb") as f:
        f.write(make_test_wav_bytes(1.0))

    call_count = 0

    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return MockHttpResponse(500, json_data={"error": "Internal server error"})

    monkeypatch.setattr(gnani.requests, "post", mock_post)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_STT_API_KEY", "mock-stt-key")

    with pytest.raises(gnani.GnaniError) as exc:
        prisma.transcribe(wav_path, language="hi")

    assert exc.value.code == "gnani_unreachable"
    assert call_count == 2  # Retried once on 5xx


def test_stt_malformed_response_json(tmp_path, monkeypatch):
    """Non-JSON response from STT service produces clean gnani_rejected error."""
    wav_path = str(tmp_path / "test.wav")
    with open(wav_path, "wb") as f:
        f.write(make_test_wav_bytes(1.0))

    mock_resp = MockHttpResponse(200, content=b"<html>Bad Gateway</html>")
    monkeypatch.setattr(gnani.requests, "post", lambda *a, **kw: mock_resp)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_STT_API_KEY", "mock-stt-key")

    with pytest.raises(gnani.GnaniError) as exc:
        prisma.transcribe(wav_path, language="hi")

    assert exc.value.code == "gnani_rejected"
    assert "malformed response" in exc.value.detail


def test_stt_missing_transcript_field(tmp_path, monkeypatch):
    """JSON response missing transcript key produces gnani_rejected error."""
    wav_path = str(tmp_path / "test.wav")
    with open(wav_path, "wb") as f:
        f.write(make_test_wav_bytes(1.0))

    mock_resp = MockHttpResponse(200, json_data={"success": True, "data": {}})
    monkeypatch.setattr(gnani.requests, "post", lambda *a, **kw: mock_resp)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_STT_API_KEY", "mock-stt-key")

    with pytest.raises(gnani.GnaniError) as exc:
        prisma.transcribe(wav_path, language="hi")

    assert exc.value.code == "gnani_rejected"
    assert "missing the transcript field" in exc.value.detail


def test_stt_rate_limit_and_daily_limit(tmp_path, monkeypatch):
    """Global limit and user daily limit reject before making network calls."""
    wav_path = str(tmp_path / "test.wav")
    with open(wav_path, "wb") as f:
        f.write(make_test_wav_bytes(1.0))

    db_dir = tmp_path / "data"
    db_dir.mkdir()
    monkeypatch.setattr(db, "DATA_DIR", str(db_dir))
    monkeypatch.setattr(db, "DB_PATH", str(db_dir / "app.db"))
    db.init()

    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_STT_API_KEY", "mock-stt-key")

    # Exceed global limit
    monkeypatch.setenv("GNANI_CALL_LIMIT", "0")
    with pytest.raises(gnani.GnaniError) as exc_limit:
        gnani.post("stt", prisma.URL, data={}, files={})
    assert exc_limit.value.status == 429
    assert exc_limit.value.code == "credit_limit_reached"

    # Exceed user daily limit
    monkeypatch.setenv("GNANI_CALL_LIMIT", "1000")
    monkeypatch.setenv("STT_DAILY_LIMIT", "0")
    monkeypatch.delenv("LIMIT_EXEMPT_EMAILS", raising=False)
    monkeypatch.delenv("OWNER_EMAIL", raising=False)
    user_id = db.execute("INSERT INTO users (name, email, password_hash, language, consent_given_at)"
                         " VALUES ('A', 'a@example.com', 'x', 'hi', '2026-01-01')")
    with pytest.raises(gnani.GnaniError) as exc_cap:
        gnani.post("stt", prisma.URL, user_id=user_id, quota="stt", data={}, files={})
    assert exc_cap.value.status == 429
    assert exc_cap.value.code == "daily_limit" and exc_cap.value.extra["kind"] == "stt"


# =============================================================================
# TTS Pipeline Hardening Tests
# =============================================================================

def test_tts_successful_response(tmp_path, monkeypatch):
    """Timbre TTS returns valid audio WAV and caches it."""
    valid_wav = make_test_wav_bytes(1.0)
    mock_resp = MockHttpResponse(200, content=valid_wav)

    monkeypatch.setattr(gnani.requests, "post", lambda *a, **kw: mock_resp)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_TTS_API_KEY", "mock-tts-key")

    out_path = speak.synthesize("नमस्ते", language="hi", cache_dir=str(tmp_path))
    assert os.path.exists(out_path)
    assert os.path.getsize(out_path) == len(valid_wav)


def test_tts_text_validation():
    """Empty or whitespace text raises ValueError without API calls."""
    with pytest.raises(ValueError, match="cannot be empty"):
        speak.synthesize("", language="hi")
    with pytest.raises(ValueError, match="cannot be empty"):
        speak.synthesize("   ", language="hi")


def test_tts_language_validation():
    """Unsupported language raises ValueError without API calls."""
    with pytest.raises(ValueError, match="unsupported language"):
        speak.synthesize("Bonjour", language="fr")


def test_tts_empty_audio_response(tmp_path, monkeypatch):
    """Empty audio response from TTS raises gnani_rejected without saving to cache."""
    mock_resp = MockHttpResponse(200, content=b"")
    monkeypatch.setattr(gnani.requests, "post", lambda *a, **kw: mock_resp)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_TTS_API_KEY", "mock-tts-key")

    with pytest.raises(gnani.GnaniError) as exc:
        speak.synthesize("नमस्ते", language="hi", cache_dir=str(tmp_path))

    assert exc.value.code == "gnani_rejected"
    assert "empty or invalid audio" in exc.value.detail


def test_tts_invalid_audio_response(tmp_path, monkeypatch):
    """Corrupted audio response (too short or bad header) raises gnani_rejected."""
    mock_resp = MockHttpResponse(200, content=b"RIFFcorruptedpayloadshort")
    monkeypatch.setattr(gnani.requests, "post", lambda *a, **kw: mock_resp)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_TTS_API_KEY", "mock-tts-key")

    with pytest.raises(gnani.GnaniError) as exc:
        speak.synthesize("नमस्ते", language="hi", cache_dir=str(tmp_path))

    assert exc.value.code == "gnani_rejected"
    assert "empty or invalid audio" in exc.value.detail


def test_tts_provider_timeout(tmp_path, monkeypatch):
    """Network timeout during TTS synthesis produces gnani_unreachable."""
    def mock_post(*args, **kwargs):
        raise requests.Timeout("Timed out")

    monkeypatch.setattr(gnani.requests, "post", mock_post)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_TTS_API_KEY", "mock-tts-key")

    with pytest.raises(gnani.GnaniError) as exc:
        speak.synthesize("नमस्ते", language="hi", cache_dir=str(tmp_path))

    assert exc.value.code == "gnani_unreachable"


def test_tts_provider_500_server_error(tmp_path, monkeypatch):
    """HTTP 500 error from TTS produces gnani_unreachable."""
    mock_resp = MockHttpResponse(500, content=b"Server error")
    monkeypatch.setattr(gnani.requests, "post", lambda *a, **kw: mock_resp)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_TTS_API_KEY", "mock-tts-key")

    with pytest.raises(gnani.GnaniError) as exc:
        speak.synthesize("नमस्ते", language="hi", cache_dir=str(tmp_path))

    assert exc.value.code == "gnani_unreachable"


def test_voice_clone_malformed_json(tmp_path, monkeypatch):
    """Malformed JSON response from voice clone endpoint produces gnani_rejected."""
    wav_path = str(tmp_path / "voice.wav")
    with open(wav_path, "wb") as f:
        f.write(make_test_wav_bytes(6.0))

    mock_resp = MockHttpResponse(200, content=b"not json")
    monkeypatch.setattr(gnani.requests, "post", lambda *a, **kw: mock_resp)
    monkeypatch.delenv("GNANI_MOCK", raising=False)
    monkeypatch.setenv("GNANI_TTS_API_KEY", "mock-tts-key")

    with pytest.raises(gnani.GnaniError) as exc:
        speak.clone_voice(wav_path, cache_dir=str(tmp_path))

    assert exc.value.code == "gnani_rejected"
    assert "malformed response" in exc.value.detail


def test_secrets_masked_in_error_reasons(monkeypatch):
    """Ensure API key values are never leaked in error reasons or logs."""
    secret_key = "secret-vachana-key-xyz123"
    monkeypatch.setenv("GNANI_STT_API_KEY", secret_key)

    mock_resp = MockHttpResponse(400, json_data={"error": {"message": f"Invalid key: {secret_key}"}})
    sanitized = gnani.reason(mock_resp)
    assert secret_key not in sanitized
    assert "[REDACTED]" in sanitized
