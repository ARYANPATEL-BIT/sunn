"""Unit and integration tests for Groq Cloud AI integration hardening and model resilience.

All tests use mocked HTTP responses; ZERO live API calls or credits are consumed.
"""
import json as json_lib
from collections import defaultdict, deque
import httpx
import pytest

import llm_judge
import log
import matcher
import trainings


class MockGroqResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text if text else (json_lib.dumps(json_data) if json_data is not None else "")
        self.headers = {"content-type": "application/json"}

    def json(self):
        if self._json_data is not None:
            return self._json_data
        raise json_lib.JSONDecodeError("Invalid JSON", self.text, 0)

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
            raise httpx.HTTPStatusError(f"HTTP {self.status_code}", request=request, response=self)


@pytest.fixture(autouse=True)
def reset_groq_state(monkeypatch):
    monkeypatch.setattr(llm_judge, "_cache", {})
    monkeypatch.setattr(llm_judge, "_calls", defaultdict(deque))
    monkeypatch.setattr(trainings, "_alternatives_cache", {})
    monkeypatch.setattr(trainings, "_assistant_calls_today", defaultdict(int))


def test_groq_model_and_base_url_default(monkeypatch):
    """Groq requests target https://api.groq.com/openai/v1 and default to openai/gpt-oss-120b."""
    captured = {}

    def mock_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        payload = {"choices": [{"message": {"content": json_lib.dumps({"choice": "1", "confidence": 0.9, "reason": "test"})}}]}
        return MockGroqResponse(200, json_data=payload)

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "mock-groq-secret-key-123")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    candidates = [{"id": "1", "score": 0.8}, {"id": "2", "score": 0.7}]
    verdict = llm_judge.ask("paani", candidates, {"place": "home"})

    assert captured["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer mock-groq-secret-key-123"
    assert captured["json"]["model"] == "openai/gpt-oss-120b"
    assert captured["json"]["reasoning_effort"] == "low"
    assert verdict == {"choice": "1", "confidence": 0.9, "reason": "test"}


def test_groq_missing_api_key_returns_none_safely(monkeypatch):
    """When GROQ_API_KEY and LLM_API_KEY are missing, ask() returns None without unhandled crashes."""
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    verdict = llm_judge.ask("paani", [{"id": "1"}], {})
    assert verdict is None

    alt = trainings.call_groq_alternatives("पानी चाहिए", "hi", ["p"])
    assert alt is None


def test_groq_disabled_mode_skips_calls(monkeypatch):
    """When LLM_ENABLED is false, no HTTP call is dispatched."""
    called = False

    def mock_post(*args, **kwargs):
        nonlocal called
        called = True
        return MockGroqResponse(200)

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setattr(trainings.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "0")

    ranked = [{"phrase_id": 1, "text": "पानी", "score": 75.0, "urgent": False}]
    assert not llm_judge.should_ask("paani", ranked)


def test_groq_invalid_credentials_401_handled_gracefully(monkeypatch):
    """HTTP 401 returns None and logs failure without raising unhandled exceptions or looping."""
    call_count = 0

    def mock_post(url, headers=None, json=None, timeout=None):
        nonlocal call_count
        call_count += 1
        return MockGroqResponse(401, json_data={"error": {"message": "Invalid API Key", "type": "invalid_request_error"}})

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "bad-key")

    verdict = llm_judge.ask("paani", [{"id": "1"}], {})
    assert verdict is None
    assert call_count == 1  # No uncontrolled retry loop


def test_groq_unsupported_reasoning_effort_retry_fallback(monkeypatch):
    """If provider returns HTTP 400 for reasoning_effort, request retries once without it."""
    payloads = []

    def mock_post(url, headers=None, json=None, timeout=None):
        payloads.append(json)
        if "reasoning_effort" in json:
            return MockGroqResponse(400, json_data={"error": {"message": "reasoning_effort is not supported"}})
        resp_data = {"choices": [{"message": {"content": "{\"choice\": \"1\", \"confidence\": 0.85, \"reason\": \"fallback ok\"}"}}]}
        return MockGroqResponse(200, json_data=resp_data)

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")
    monkeypatch.setenv("LLM_REASONING_EFFORT", "high")

    verdict = llm_judge.ask("paani", [{"id": "1"}], {})
    assert len(payloads) == 2
    assert "reasoning_effort" in payloads[0]
    assert "reasoning_effort" not in payloads[1]
    assert verdict["choice"] == "1"
    assert verdict["reason"] == "fallback ok"


def test_groq_rate_limit_429_handled(monkeypatch):
    """HTTP 429 is caught cleanly and returns None without raising."""
    def mock_post(url, headers=None, json=None, timeout=None):
        return MockGroqResponse(429, json_data={"error": {"message": "Rate limit reached", "type": "rate_limit_exceeded"}})

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")

    verdict = llm_judge.ask("paani", [{"id": "1"}], {})
    assert verdict is None


def test_groq_timeout_handled(monkeypatch):
    """Timeout exception is caught cleanly and returns None."""
    def mock_post(url, headers=None, json=None, timeout=None):
        raise httpx.TimeoutException("Connection timed out")

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")

    verdict = llm_judge.ask("paani", [{"id": "1"}], {})
    assert verdict is None


def test_groq_500_server_error_handled(monkeypatch):
    """HTTP 500 server error returns None without crashing."""
    def mock_post(url, headers=None, json=None, timeout=None):
        return MockGroqResponse(500, json_data={"error": {"message": "Internal Groq Error"}})

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")

    verdict = llm_judge.ask("paani", [{"id": "1"}], {})
    assert verdict is None


def test_groq_malformed_json_response(monkeypatch):
    """Non-JSON response from Groq is handled safely without raising."""
    def mock_post(url, headers=None, json=None, timeout=None):
        return MockGroqResponse(200, text="<html>502 Bad Gateway</html>")

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")

    verdict = llm_judge.ask("paani", [{"id": "1"}], {})
    assert verdict is None


def test_groq_empty_response_choices(monkeypatch):
    """Response with empty choices list returns None."""
    def mock_post(url, headers=None, json=None, timeout=None):
        return MockGroqResponse(200, json_data={"choices": []})

    monkeypatch.setattr(llm_judge.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "mock-key")

    verdict = llm_judge.ask("paani", [{"id": "1"}], {})
    assert verdict is None


def test_groq_rate_limit_slot_per_user(monkeypatch):
    """Rate limit per user allows LLM_RATE_PER_MIN calls then rejects additional slots."""
    monkeypatch.setenv("LLM_RATE_PER_MIN", "3")

    user_a = "user-100"
    user_b = "user-200"

    assert llm_judge.take_slot(user_a) is True
    assert llm_judge.take_slot(user_a) is True
    assert llm_judge.take_slot(user_a) is True
    assert llm_judge.take_slot(user_a) is False  # user A exhausted

    assert llm_judge.take_slot(user_b) is True  # user B has separate rate limit window


def test_groq_judge_tenant_isolated_cache(monkeypatch):
    """Judge cache keys isolate results between different users."""
    called_users = []

    def mock_ask(heard, candidates, context):
        return {"choice": "1", "confidence": 0.9, "reason": "test"}

    monkeypatch.setattr(llm_judge, "ask", mock_ask)
    ranked = [{"phrase_id": 1, "text": "पानी चाहिए", "score": 80.0, "urgent": False, "composed": False, "parts": {}},
              {"phrase_id": 2, "text": "खाना चाहिए", "score": 70.0, "urgent": False, "composed": False, "parts": {}}]

    res1 = llm_judge.judge("baani", ranked, "home", [], {}, user_id=1)
    assert res1["chosen_by"] == "judge"

    # User 1 second call hits cache
    def fail_ask(*a, **kw):
        pytest.fail("Should have hit user 1 cache")

    monkeypatch.setattr(llm_judge, "ask", fail_ask)
    res1_cached = llm_judge.judge("baani", ranked, "home", [], {}, user_id=1)
    assert res1_cached["chosen_by"] == "judge"

    # User 2 call does NOT hit user 1's cache
    user2_called = False
    def user2_ask(*a, **kw):
        nonlocal user2_called
        user2_called = True
        return {"choice": "2", "confidence": 0.85, "reason": "user2 match"}

    monkeypatch.setattr(llm_judge, "ask", user2_ask)
    res2 = llm_judge.judge("baani", ranked, "home", [], {}, user_id=2)
    assert user2_called is True
    assert res2["verdict"]["choice"] == "2"


def test_groq_alternatives_meaning_preservation_and_urgent_protection(monkeypatch):
    """Dismissive phrases are rejected for urgent inputs; meaning is preserved."""
    def mock_post(url, headers=None, json=None, timeout=None):
        # Model suggests one dismissive and two urgent-preserving alternatives
        payload = {
            "choices": [{
                "message": {
                    "content": json_lib.dumps({
                        "meaning_en": "I need help with pain",
                        "alternatives": [
                            {"text": "सब ठीक है", "latin": "sab theek hai"},  # dismissive -> must be filtered
                            {"text": "मदद करें", "latin": "madad karein"},      # valid urgent alternative
                            {"text": "तकलीफ़ है", "latin": "takleef hai"},     # valid urgent alternative
                        ]
                    })
                }
            }]
        }
        return MockGroqResponse(200, json_data=payload)

    monkeypatch.setattr(trainings.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

    res = trainings.call_groq_alternatives("दर्द हो रहा है", "hi", ["d"])
    assert res is not None
    assert len(res.alternatives) == 2
    # Ensure dismissive alternative was stripped
    assert not any("theek" in a.latin.lower() or "ठीक" in a.text for a in res.alternatives)
    assert any("madad" in a.latin.lower() for a in res.alternatives)


def test_groq_alternatives_english_support(monkeypatch):
    """English language requests generate natural English alternatives with valid metadata."""
    def mock_post(url, headers=None, json=None, timeout=None):
        payload = {
            "choices": [{
                "message": {
                    "content": json_lib.dumps({
                        "meaning_en": "I would like some water",
                        "alternatives": [
                            {"text": "Please give me water", "latin": "Please give me water"},
                            {"text": "Water please", "latin": "Water please"},
                        ]
                    })
                }
            }]
        }
        return MockGroqResponse(200, json_data=payload)

    monkeypatch.setattr(trainings.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

    res = trainings.call_groq_alternatives("I need water", "en", ["w"])
    assert res is not None
    assert res.meaning_en == "I would like some water"
    assert len(res.alternatives) == 2
    texts = [a.text for a in res.alternatives]
    assert "Please give me water" in texts and "Water please" in texts


def test_groq_alternatives_library_fallback_when_unreachable(env, monkeypatch):
    """When Groq is unreachable, alternatives route cleanly falls back to library without 500 error."""
    def mock_post(*a, **kw):
        raise httpx.ConnectError("Groq service unreachable")

    monkeypatch.setattr(trainings.httpx, "post", mock_post)
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

    client = env.signup()
    # Search for an existing phrase in library
    res = client.post("/me/trainings/alternatives", json={"text": "पानी चाहिए", "lang": "hi"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["alternatives"]) > 0
    assert all(a["source"] == "library" for a in data["alternatives"])
