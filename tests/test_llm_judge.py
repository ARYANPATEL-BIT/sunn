"""The judge (src/llm_judge.py) against a fake LLM, and the reranker (src/reranker.py) without its
model. No test reaches an LLM: httpx.post is replaced, and conftest points LLM_BASE_URL nowhere."""
import json
import sys
from collections import defaultdict, deque

import httpx
import numpy as np
import pytest

import llm_judge
import log
import reranker


class FakeLLM:
    """Stands in for httpx.post in llm_judge.py. Answers content (a dict is sent as JSON) with
    status, or raises error; keeps every request body."""

    def __init__(self):
        self.content, self.status, self.error, self.bodies = None, 200, None, []

    def __call__(self, url, **request):
        assert url == "https://llm.invalid/v1/chat/completions"
        assert request["headers"]["Authorization"] in ("Bearer test-llm-key", "Bearer test-groq-key") and request["timeout"] == 3
        self.bodies.append(request["json"])
        if self.error:
            raise self.error
        content = self.content if isinstance(self.content, str) else json.dumps(self.content)
        return httpx.Response(self.status, json={"choices": [{"message": {"content": content}}]},
                              request=httpx.Request("POST", url))


@pytest.fixture
def llm(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("LLM_MODE", "always")
    monkeypatch.setattr(llm_judge, "_cache", {})
    monkeypatch.setattr(llm_judge, "_calls", defaultdict(deque))
    fake = FakeLLM()
    monkeypatch.setattr(llm_judge.httpx, "post", fake)
    return fake


def ranked(*texts):
    """Candidates as matcher.rank gives them, best first, 5 points apart, ids 1, 2, ..."""
    return [{"phrase_id": i + 1, "text": text, "score": 80.0 - 5 * i, "urgent": False, "composed": False,
             "parts": {"similarity": 80.0 - 5 * i, "context": 0, "freq": 0, "time": 0}} for i, text in enumerate(texts)]


PHRASES = ranked("पानी चाहिए", "खाना दे दो", "चाय पीनी है", "दूध चाहिए", "दवाई दे दो")
MATCHER_TOP_3 = ["पानी चाहिए", "खाना दे दो", "चाय पीनी है"]


def judge(candidates=PHRASES, heard="baani chaiye", user_id=1):
    return llm_judge.judge(heard, candidates, "home", ["चाय पीनी है"], {1: 4}, user_id)


def shown(result):
    return [c["text"] for c in result["shown"]]


def test_a_confident_valid_choice_goes_first_with_its_reason(llm):
    llm.content = {"choice": "4", "confidence": 0.9, "reason": "sounds like doodh chahiye"}
    result = judge()
    assert shown(result) == ["दूध चाहिए", "पानी चाहिए", "खाना दे दो"]
    assert result["chosen_by"] == "judge" and result["reason"] == "sounds like doodh chahiye"


def test_the_request_sends_only_text_as_specified(llm):
    llm.content = {"choice": "1", "confidence": 0.9, "reason": "paani"}
    judge()
    body = llm.bodies[0]
    assert (body["temperature"], body["max_tokens"], body["response_format"]) == (0, 120, {"type": "json_object"})
    assert body["messages"][0] == {"role": "system", "content": llm_judge.SYSTEM}
    message = body["messages"][1]["content"]
    heard, rest = message.split(". our model ranked these candidates (best first): ")
    candidates, context = rest.removesuffix(". which candidate did they mean? write the reason in english.").split(
        ". context: ")
    assert heard == "the person speaks hindi, written in devanagari script. the stt registered: baani chaiye"
    candidates, context = json.loads(candidates), json.loads(context)
    assert [c["id"] for c in candidates] == ["1", "2", "3", "4", "5"]
    assert candidates[0] == {"id": "1", "hindi": "पानी चाहिए", "latin": "paani chahiye", "meaning_en": "I need water",
                             "score": 0.8, "times_used": 4}
    assert context.pop("time_of_day") in ("morning", "afternoon", "evening", "night")
    assert context == {"place": "home", "recent_phrases": ["चाय पीनी है"]}


@pytest.mark.parametrize("answer", [
    {"choice": "9", "confidence": 0.9, "reason": "an id not in the list"},
    {"choice": "none", "confidence": 0.9, "reason": "no candidate fits"},
    {"choice": "4", "confidence": 0.3, "reason": "unsure"},
    {"choice": "4", "confidence": "high", "reason": "not a number"},
    "this is not json",
])
def test_anything_but_a_confident_valid_choice_keeps_the_matchers_order(llm, answer):
    llm.content = answer
    result = judge()
    assert shown(result) == MATCHER_TOP_3 and result["chosen_by"] == "matcher" and result["reason"] is None


@pytest.mark.parametrize("error, status", [(httpx.ReadTimeout("slow"), 200), (None, 429),
                                           (httpx.ConnectError("unreachable"), 200)])
def test_a_failed_call_keeps_the_matchers_order_and_logs_one_line_without_key_or_text(llm, monkeypatch, error, status):
    llm.error, llm.status = error, status
    events = []
    monkeypatch.setattr(log, "event", lambda name, **fields: events.append((name, fields)))
    result = judge()
    assert shown(result) == MATCHER_TOP_3 and result["chosen_by"] == "matcher"
    assert len(events) == 1 and events[0][0] == "llm_call" and events[0][1]["outcome"] != "ok"
    assert not any(secret in str(events) for secret in ("test-llm-key", "baani", "पानी"))


def test_uncertain_mode_asks_only_when_the_matcher_is_unsure(llm, monkeypatch):
    monkeypatch.setenv("LLM_MODE", "uncertain")
    clear = [dict(PHRASES[0], score=95.0), dict(PHRASES[1], score=60.0)]
    words = "mujhe paani chahiye abhi"
    assert not llm_judge.should_ask(words, clear)
    assert llm_judge.should_ask(words, [clear[0], dict(clear[1], score=85.0)])  # within LLM_MARGIN (0.15)
    assert llm_judge.should_ask(words, [dict(clear[0], score=55.0), dict(clear[1], score=20.0)])  # under LLM_MIN_SCORE
    assert llm_judge.should_ask("paani chahiye", clear)  # 2 words or fewer
    monkeypatch.setenv("LLM_MODE", "always")
    assert llm_judge.should_ask(words, clear)
    assert not llm_judge.should_ask(words, clear[:1])  # nothing to choose between
    monkeypatch.setenv("LLM_ENABLED", "0")
    assert not llm_judge.should_ask(words, clear)


def test_an_urgent_phrase_in_the_top_3_stays_shown(llm):
    llm.content = {"choice": "5", "confidence": 0.9, "reason": "sounds like dawai"}
    result = judge(ranked("पानी चाहिए", "खाना दे दो", "दर्द हो रहा है", "दूध चाहिए", "दवाई दे दो"))
    assert shown(result) == ["दवाई दे दो", "पानी चाहिए", "दर्द हो रहा है"]


def test_answers_are_cached_and_calls_limited_per_user(llm, monkeypatch):
    monkeypatch.setenv("LLM_RATE_PER_MIN", "2")
    llm.content = {"choice": "4", "confidence": 0.9, "reason": "doodh"}
    judge(), judge()
    assert len(llm.bodies) == 1  # the same heard text, candidates and place
    judge(heard="doodh")
    assert judge(heard="dudh chahiye")["chosen_by"] == "matcher" and len(llm.bodies) == 2  # 3rd in a minute
    assert judge(heard="dudh chahiye", user_id=2)["chosen_by"] == "judge" and len(llm.bodies) == 3


def enroll(env, client, *texts):
    for text in texts:
        env.enroll_phrase(client, text)
    return {p["text"]: p["id"] for p in client.get("/me/phrases").json()}


def test_with_the_judge_and_reranker_off_recognition_is_as_before(env, monkeypatch):
    monkeypatch.setattr(llm_judge.httpx, "post", lambda *a, **k: pytest.fail("LLM_ENABLED is off"))
    client = env.signup()
    enroll(env, client, "पानी चाहिए", "खाना दे दो", "चाय पीनी है", "दूध चाहिए")
    result = env.recognize(client, "पानी चाहिए")
    assert result["candidates"][0]["text"] == "पानी चाहिए" and len(result["candidates"]) == 3
    assert not any("rerank" in c["parts"] for c in result["candidates"])
    assert (result["chosen_by"], result["reason"]) == ("matcher", None)
    assert result["timings_ms"]["rerank"] is None and result["timings_ms"]["llm"] is None


def test_the_judge_reorders_a_recognition_and_sends_nothing_personal(env, llm):
    client = env.signup()
    ids = enroll(env, client, "पानी चाहिए", "खाना दे दो", "चाय पीनी है")
    llm.content = {"choice": str(ids["चाय पीनी है"]), "confidence": 0.8, "reason": "they often ask for tea"}
    result = env.recognize(client, "पानी चाहिए", context="home")
    assert [c["text"] for c in result["candidates"]] == ["चाय पीनी है", "पानी चाहिए", "खाना दे दो"]
    assert (result["chosen_by"], result["reason"]) == ("judge", "they often ask for tea")
    assert result["timings_ms"]["llm"] is not None
    me, sent = client.get("/auth/me").json(), json.dumps(llm.bodies, ensure_ascii=False)
    assert me["email"] not in sent and me["name"] not in sent


@pytest.mark.parametrize("files", [{}, {"model.onnx": b"not a model", "tokenizer.json": b"{}"}])
def test_a_missing_or_broken_reranker_is_one_warning_and_recognition_goes_on(env, monkeypatch, tmp_path, capsys, files):
    for name, content in files.items():
        (tmp_path / name).write_bytes(content)
    monkeypatch.setattr(reranker, "_model", None)
    monkeypatch.setenv("RERANKER_ENABLED", "1")
    monkeypatch.setenv("RERANKER_PATH", str(tmp_path / "model.onnx"))
    reranker.load()
    assert not reranker.on() and capsys.readouterr().err.count("warning: the reranker is off") == 1
    client = env.signup()
    enroll(env, client, "पानी चाहिए", "खाना दे दो")
    result = env.recognize(client, "पानी चाहिए")
    assert result["candidates"][0]["text"] == "पानी चाहिए" and result["timings_ms"]["rerank"] is None


def test_the_reranker_imports_nothing_when_off(monkeypatch):
    monkeypatch.setitem(sys.modules, "onnxruntime", None)  # importing it would fail
    monkeypatch.setattr(reranker, "_model", None)
    reranker.load()
    assert not reranker.on()


def test_the_reranker_adds_its_weighted_part_and_resorts(monkeypatch):
    class Encoding:
        ids = attention_mask = type_ids = [1, 2]

    class Tokenizer:
        def encode_batch(self, pairs):
            return [Encoding() for _ in pairs]

    class Session:  # sure of the second candidate
        def run(self, names, feed):
            return [np.array([[0.0], [10.0], [0.0]])]

    monkeypatch.setattr(reranker, "_model", (Session(), Tokenizer()))
    monkeypatch.setenv("RERANKER_WEIGHT", "20")
    out = reranker.rescore("khaana do", ranked("पानी चाहिए", "खाना दे दो", "चाय पीनी है"))
    assert [c["text"] for c in out] == ["खाना दे दो", "पानी चाहिए", "चाय पीनी है"]
    assert out[0]["parts"]["rerank"] == 20.0 and out[0]["score"] == 95.0
    assert all(c["score"] == round(sum(c["parts"].values()), 1) for c in out)
