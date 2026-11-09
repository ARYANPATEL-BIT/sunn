"""The judge (LLM_ENABLED): after the matcher has ranked a person's phrases, an LLM re-picks
among the top 5, over any OpenAI-compatible /chat/completions.

It is sent text only: what Prisma heard, the place, the time of day, the last 3 phrases the
person spoke and the 5 candidates. Never a name, email, user id or audio. It can only choose one
of those candidates, or none. Anything short of a confident valid answer (unsure, "none", a
timeout, a network error, a 429, malformed JSON) keeps the matcher's order; nothing here fails
the request, and a failure is one log line with neither the key nor the person's text."""
import hashlib
import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

import httpx

import languages
import log
import matcher

SYSTEM = (
    "you help a person with unclear speech be understood. a speech recognizer heard their words and is often"
    " wrong in consistent ways: b/p, d/t, k/g swaps, dropped h sounds, short and long vowels mixed up, chopped"
    " word endings, merged or split words, hindi written in english letters. pick which candidate they most"
    " likely meant: first by sound similarity, then by the place, time of day and recent phrases. you must"
    ' answer with one candidate id from the list, or "none" if no candidate fits. never write a new phrase. if'
    " a candidate about pain, a doctor or help is plausible, do not dismiss it. reply with json only:"
    ' {"choice": "<id or none>", "confidence": <0 to 1>, "reason": "<max 12 words, plain words>"}.'
    " write the reason in the language the user message asks for."
)
USER = ("the person speaks {language}, written in {script} script. the stt registered: {heard}. our model ranked"
        " these candidates (best first): {candidates}. context: {context}. which candidate did they mean?"
        " write the reason in {reason_language}.")
TOP_K = 5  # candidates the judge chooses among
SHOWN = 3  # candidates the app shows
MIN_CONFIDENCE = 0.5  # under it, the matcher's order stands
CACHE_SECONDS = 600
# An urgent phrase in the matcher's top 3 stays shown whatever the judge picks.
URGENT_WORDS = ("pain", "hurt", "doctor", "help", "sos", "breath", "दर्द", "डॉक्टर", "मदद", "सांस", "साँस")

_cache = {}  # sha256 of (heard, candidate ids, place) -> (expires, verdict)
_calls = defaultdict(deque)  # user id -> when their calls in the last minute were sent
_lock = threading.Lock()


def setting(name, default=""):
    return os.environ.get(name, "").strip() or default


def enabled():
    return setting("LLM_ENABLED").lower() in ("1", "true", "yes", "on")


def should_ask(heard, ranked):
    """Whether to ask about ranked (the matcher's order, best first): never with fewer than 2
    candidates, since there is nothing to choose. LLM_MODE=always asks every time; uncertain (the
    default) only when the top two scores are within LLM_MARGIN, the top one is under
    LLM_MIN_SCORE (both on the 0-1 scale, score / 100) or Prisma heard 2 words or fewer."""
    if not enabled() or len(ranked) < 2:
        return False
    if setting("LLM_MODE", "uncertain") == "always":
        return True
    top, second = ranked[0]["score"] / 100, ranked[1]["score"] / 100
    return (top - second < float(setting("LLM_MARGIN", "0.15")) or top < float(setting("LLM_MIN_SCORE", "0.6"))
            or len(heard.split()) <= 2)


def candidate_id(c):
    """A phrase's id, or t<template>w<slot word> for a composed candidate, which has none yet."""
    return str(c["phrase_id"]) if c.get("phrase_id") is not None else f"t{c['template_id']}w{c['slot_word_id']}"


def describe(c, times_used, language="hi"):
    """A candidate for the judge. Its text in an Indic script goes under "hindi" for a Hindi
    speaker, as it always has, and under "native" for the rest."""
    latin, meaning = matcher.gloss(c["text"])
    native = c["text"] if languages.script_of(c["text"]) else ""
    return {"id": candidate_id(c), "hindi" if language == "hi" else "native": native,
            "latin": latin, "meaning_en": meaning, "score": round(c["score"] / 100, 2),
            "times_used": times_used.get(c.get("phrase_id"), 0)}


def is_urgent(c):
    words = f"{c['text']} {matcher.gloss(c['text'])[1]}".lower()
    return c["urgent"] or any(word in words for word in URGENT_WORDS)


def parse(content, ids):
    """The verdict {choice, confidence, reason} when content is the JSON asked for, its choice
    one of ids or "none" and its confidence a number from 0 to 1; else None."""
    answer = json.loads(content)
    if not isinstance(answer, dict):
        return None
    choice, confidence = str(answer.get("choice", "")).strip(), answer.get("confidence")
    choice = "none" if choice.lower() == "none" else choice
    if choice not in ids and choice != "none":
        return None
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        return None
    return {"choice": choice, "confidence": float(confidence),
            "reason": " ".join(str(answer.get("reason") or "").split()[:12])}


def readable(reason, language):
    """reason when it is text in language's script (Latin for English): most of its letters in
    that script, and no braces or angle brackets. Else None, and no reason is shown."""
    block = languages.LANGUAGES[language].block
    letters = [c for c in reason if c.isalpha()]
    if not letters or any(c in reason for c in "{}<>"):
        return None
    ours = sum((block[0] <= c <= block[1]) if block else c.isascii() for c in letters)
    return reason if ours >= len(letters) / 2 else None


def ask(heard, candidates, context, language="hi", reason_language="en"):
    """The model's verdict on candidates (described), or None, logged, when there isn't a valid one."""
    base = setting("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    key = setting("GROQ_API_KEY") or setting("LLM_API_KEY")
    model = setting("GROQ_MODEL") or setting("LLM_MODEL", "openai/gpt-oss-120b")
    max_tokens = int(setting("LLM_MAX_TOKENS", "120"))
    body = {"model": model, "temperature": 0, "max_tokens": max_tokens, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": USER.format(
                             language=languages.LANGUAGES[language].name.lower(),
                             script=languages.LANGUAGES[language].script.lower(),
                             heard=heard, candidates=json.dumps(candidates, ensure_ascii=False),
                             context=json.dumps(context, ensure_ascii=False),
                             reason_language=languages.LANGUAGES[reason_language].name.lower())}]}
    effort = setting("LLM_REASONING_EFFORT", "low").strip().lower()
    if effort in ("low", "medium", "high"):
        body["reasoning_effort"] = effort
    started, verdict, status = time.monotonic(), None, None
    try:
        if not (base and key and model):
            raise LookupError("GROQ_API_KEY (or LLM_API_KEY), LLM_BASE_URL, or GROQ_MODEL (or LLM_MODEL) is empty")
        headers = {"Authorization": f"Bearer {key}"}
        timeout_s = float(setting("LLM_TIMEOUT_S", "3"))
        response = httpx.post(f"{base}/chat/completions", headers=headers, json=body, timeout=timeout_s)
        status = response.status_code
        if status == 400 and "reasoning_effort" in body:
            # Model or provider does not support reasoning_effort: retry once without it
            retry_body = dict(body)
            retry_body.pop("reasoning_effort", None)
            retry_resp = httpx.post(f"{base}/chat/completions", headers=headers, json=retry_body, timeout=timeout_s)
            status = retry_resp.status_code
            if retry_resp.status_code == 200:
                response = retry_resp
        response.raise_for_status()
        verdict = parse(response.json()["choices"][0]["message"]["content"], [c["id"] for c in candidates])
        outcome = "ok" if verdict else "invalid_answer"
    except httpx.TimeoutException:
        outcome = "timeout"
    except Exception as e:  # a network error, an HTTP error like 429, an answer that isn't JSON: never fail
        outcome = type(e).__name__
    log.event("llm_call", level=logging.INFO if verdict else logging.WARNING, outcome=outcome, status=status,
              ms=round(1000 * (time.monotonic() - started)))
    return verdict


def take_slot(user_id):
    """Count a call against the user's LLM_RATE_PER_MIN, or False when it is used up."""
    with _lock:
        sent, now = _calls[user_id], time.monotonic()
        while sent and now - sent[0] >= 60:
            sent.popleft()
        if len(sent) >= int(setting("LLM_RATE_PER_MIN", "10")):
            return False
        sent.append(now)
        return True


def remember(key, verdict=None):
    """The cached verdict for key; with verdict, cache it for CACHE_SECONDS."""
    now = time.monotonic()
    with _lock:
        if verdict is not None:
            for stale in [k for k, (expires, _) in _cache.items() if expires < now]:
                del _cache[stale]
            _cache[key] = (now + CACHE_SECONDS, verdict)
        expires, found = _cache.get(key, (0, None))
        return found if expires >= now else None


def reorder(ranked, chosen):
    """The judge's pick first, then the rest in the matcher's order, SHOWN of them. An urgent
    phrase that was in the matcher's top SHOWN stays shown, in place of a non-urgent one."""
    shown = [ranked[chosen]] + [c for i, c in enumerate(ranked) if i != chosen][:SHOWN - 1]
    for c in ranked[:SHOWN]:
        if is_urgent(c) and not any(c is s for s in shown):
            spare = next((i for i in range(len(shown) - 1, 0, -1) if not is_urgent(shown[i])), None)
            if spare is not None:
                shown[spare] = c
    return shown


def judge(heard, ranked, place, recent, times_used, user_id, language="hi", reason_language="en"):
    """{shown, chosen_by, reason, verdict} for ranked, the matcher's order: shown is the SHOWN
    candidates to show, the judge's pick first when it made a confident valid one (chosen_by
    "judge", with its reason in reason_language, the interface's, or None when it isn't readable
    text in it), else the matcher's top SHOWN (chosen_by "matcher", reason None). recent is the
    last 3 phrases the person spoke; times_used is {phrase_id: uses}; language is the one they speak."""
    top = ranked[:TOP_K]
    ids = [candidate_id(c) for c in top]
    result = {"shown": ranked[:SHOWN], "chosen_by": "matcher", "reason": None, "verdict": None}
    key = hashlib.sha256(json.dumps([user_id, heard, ids, place, language, reason_language],
                                    ensure_ascii=False).encode("utf-8")).hexdigest()
    verdict = remember(key)
    if verdict is None:
        if not take_slot(user_id):
            log.event("llm_call", level=logging.WARNING, outcome="rate_limited")
            return result
        context = {"place": place, "time_of_day": matcher.time_bucket(datetime.now(timezone.utc)),
                   "recent_phrases": recent}
        verdict = ask(heard, [describe(c, times_used, language) for c in top], context, language, reason_language)
        if verdict is None:
            return result
        remember(key, verdict)
    result["verdict"] = verdict
    if verdict["choice"] != "none" and verdict["confidence"] >= MIN_CONFIDENCE:
        result.update(shown=reorder(ranked, ids.index(verdict["choice"])), chosen_by="judge",
                      reason=readable(verdict["reason"], reason_language))
    return result
