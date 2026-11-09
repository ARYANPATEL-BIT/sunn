"""Sunn in all ten languages: normalize() per script, matching per language, what Prisma and
Timbre are sent, per-language candidates, the reranker only for Hindi, the judge told the
language, and Hindi exactly as before."""
import json
import re
from pathlib import Path

import httpx
import pytest
from indic_transliteration import sanscript

import languages
import llm_judge
import matcher
import prisma
import reranker
import speak

ROOT = Path(__file__).resolve().parent.parent
OTHERS = ("ta", "te", "kn", "ml", "mr", "gu", "bn", "pa")


def bank(code):
    """[(phrase, latin, meaning)] of data/default_phrases_<code>.txt, a non-Hindi, non-English one."""
    lines = (ROOT / "data" / f"default_phrases_{code}.txt").read_text(encoding="utf-8").splitlines()
    return [tuple(part.strip() for part in line.split("|")) for line in lines if not line.startswith("#")]


@pytest.mark.parametrize("code, words", [
    ("hi", {"पानी": "pani", "दर्द": "darda", "मदद": "madada"}),
    ("mr", {"पाणी": "pani", "दुखतंय": "dukhatamya", "मदत": "madata"}),
    ("ta", {"தண்ணி": "dhanni", "வலிக்குது": "valighghudhu", "உதவி": "udhavi"}),
    ("te", {"నీళ్ళు": "nillu", "నొప్పి": "noppi", "సహాయం": "sahayam"}),
    ("kn", {"ನೀರು": "niru", "ನೋವು": "novu", "ಸಹಾಯ": "sahaya"}),
    ("ml", {"വെള്ളം": "vellam", "വേദന": "vedana", "ഡോക്ടർ": "doktar"}),
    ("gu", {"પાણી": "pani", "દુખે": "dukhe", "મદદ": "madada"}),
    ("bn", {"জল": "jala", "ব্যথা": "vyatha", "সাহায্য": "sahayya"}),
    ("pa", {"ਪਾਣੀ": "pani", "ਦਰਦ": "darada", "ਮਦਦ": "madada"}),
    ("en", {"I need Water!": "i need water", "Help,": "help", "doctor": "doctor"}),
])
def test_normalize_writes_every_script_in_plain_latin(code, words):
    for word, latin in words.items():
        assert matcher.normalize(word) == latin, (code, word)
        assert re.fullmatch(r"[a-z ]+", latin)


def test_devanagari_normalizes_exactly_as_before():
    def before(text):  # normalize() as it was when it knew only Devanagari
        text = sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
        text = "".join(c for c in text.lower() if c.isspace() or c.isalnum() or c in "ॉ")
        return " ".join(text.split())

    for line in (ROOT / "data" / "default_phrases_hi.txt").read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            assert matcher.normalize(line) == before(line), line


@pytest.mark.parametrize("code", OTHERS)
def test_a_typo_still_finds_the_phrase_in_every_language(code):
    phrases = [phrase for phrase, _, _ in bank(code)]
    candidates = [{"key": i, "text": p, "fingerprints": [p], "contexts": []} for i, p in enumerate(phrases)]
    for target in (phrases[0], phrases[1], phrases[16]):  # help, water, call the doctor
        typo = target[:2] + target[3:]  # one letter dropped
        assert typo != target
        assert matcher.rank(typo, candidates)[0]["text"] == target, (code, target, typo)


@pytest.mark.parametrize("code", OTHERS)
def test_every_bank_has_the_hindi_meanings_and_the_urgent_phrases(code):
    english = [line for line in (ROOT / "data" / "default_phrases_en.txt").read_text(encoding="utf-8").splitlines()
               if not line.startswith("#")]
    rows = bank(code)
    assert [meaning for _, _, meaning in rows] == english
    meanings = {meaning for _, _, meaning in rows}
    assert {"I need help", "I'm in pain", "Call the doctor", "I can't breathe properly"} <= meanings
    block = languages.LANGUAGES[code].block
    for phrase, latin, _ in rows:
        assert languages.in_script(phrase, block) and re.fullmatch(r"[a-z ,]+", latin), (code, phrase)
    header = (ROOT / "data" / f"default_phrases_{code}.txt").read_text(encoding="utf-8").splitlines()[0]
    assert header.startswith("# Machine-written")


def test_the_quick_start_phrases_are_in_the_banks():
    source = (ROOT / "web" / "src" / "quickstart.js").read_text(encoding="utf-8")
    for code in OTHERS:
        listed = re.search(rf"\n  {code}: \[(.*?)\]", source, re.S).group(1)
        texts = re.findall(r"'([^']+)'", listed)
        assert len(texts) == 10 and set(texts) <= {phrase for phrase, _, _ in bank(code)}, code


# --- what Prisma and Timbre are sent


@pytest.mark.parametrize("code", languages.CODES)
def test_prisma_and_timbre_get_the_users_language(env, code):
    client = env.signup(code)
    phrases = client.get("/me/phrases").json()
    assert phrases and {p["language"] for p in phrases} == {code}
    assert sum(p["urgent"] for p in phrases) == 2  # help and pain
    water = phrases[1]["text"]
    env.enroll_phrase(client, water)
    assert env.fake.sent("stt")[-1]["data"] == {"language_code": f"{code}-IN", "format": "verbatim"}
    client.post("/speak", json={"text": water}).raise_for_status()
    body = env.fake.sent("tts")[-1]["json"]
    assert (body["language"], body["voice"], body["model"]) == (f"{code}-IN", speak.VOICES[code], "timbre-v2.5")


def test_hindi_requests_are_exactly_as_before():
    assert prisma.request_form("hi") == {"language_code": "hi-IN", "format": "verbatim"}
    assert speak.request_body("नमस्ते", "hi") == {
        "text": "नमस्ते", "voice": "Nalini", "model": "timbre-v2.5", "language": "hi-IN",
        "audio_config": {"sample_rate": 48000, "num_channels": 1, "sample_width": 2, "encoding": "linear_pcm",
                         "container": "wav"}}


def test_a_phrase_is_spoken_in_its_own_language(env):
    client = env.signup("hi")
    client.patch("/me", json={"language": "ta"}).raise_for_status()
    client.post("/speak", json={"text": "पानी चाहिए"}).raise_for_status()  # a Hindi phrase
    assert env.fake.sent("tts")[-1]["json"]["language"] == "hi-IN"
    client.post("/speak", json={"text": "வணக்கம்"}).raise_for_status()  # no phrase yet: the user's language
    assert env.fake.sent("tts")[-1]["json"]["language"] == "ta-IN"


def test_own_voice_is_offered_only_in_hindi(env):
    client = env.signup("hi")
    assert client.get("/auth/me").json()["can_clone_voice"] is True
    client.post("/me/voice", data={"consent": "true"}, files=env.recording(6)).raise_for_status()
    client.patch("/me", json={"use_own_voice": True}).raise_for_status()
    client.post("/speak", json={"text": "पानी चाहिए"}).raise_for_status()
    assert "speaker_embedding" in env.fake.sent("tts")[-1]["json"]
    for code in ("en", "ta"):
        assert client.patch("/me", json={"language": code}).json()["can_clone_voice"] is False
    client.post("/me/phrases/default").raise_for_status()
    client.post("/speak", json={"text": "வணக்கம்"}).raise_for_status()
    sent = env.fake.sent("tts")[-1]["json"]
    assert "speaker_embedding" not in sent and sent["voice"] == "Noopur"


# --- candidates per language


def test_candidates_are_only_the_recordings_language_and_english(env):
    client = env.signup("hi")
    water_hi = env.enroll_phrase(client, "पानी चाहिए", "paani chahiye")
    client.patch("/me", json={"language": "en"}).raise_for_status()
    client.post("/me/phrases/default").raise_for_status()
    water_en = env.enroll_phrase(client, "I need water")
    client.patch("/me", json={"language": "ta"}).raise_for_status()
    client.post("/me/phrases/default").raise_for_status()
    water_ta = env.enroll_phrase(client, "தண்ணி வேணும்")

    heard = env.recognize(client, "தண்ணி வேணும்")["candidates"]
    assert [c["phrase_id"] for c in heard] == [water_ta["id"], water_en["id"]]
    assert water_hi["id"] not in [c["phrase_id"] for c in heard]
    assert env.fake.sent("stt")[-1]["data"]["language_code"] == "ta-IN"

    client.patch("/me", json={"language": "hi"}).raise_for_status()
    heard = env.recognize(client, "paani chahiye")["candidates"]
    assert heard[0]["phrase_id"] == water_hi["id"] and water_ta["id"] not in [c["phrase_id"] for c in heard]


@pytest.mark.parametrize("code, reranked", [("hi", True), ("ta", False), ("en", False)])
def test_the_reranker_runs_only_for_hindi(env, monkeypatch, code, reranked):
    monkeypatch.setenv("RERANKER_ENABLED", "1")
    monkeypatch.setattr(reranker, "_model", object())  # "loaded"
    calls = []
    monkeypatch.setattr(reranker, "rescore", lambda heard, ranked: calls.append(heard) or ranked)
    client = env.signup(code)
    water = client.get("/me/phrases").json()[1]["text"]
    env.enroll_phrase(client, water)
    timings = env.recognize(client, water)["timings_ms"]
    assert bool(calls) == reranked and (timings["rerank"] is not None) == reranked


# --- the judge


class FakeLLM:
    def __init__(self, reason):
        self.reason, self.bodies = reason, []

    def __call__(self, url, **request):
        self.bodies.append(request["json"])
        content = json.dumps({"choice": "2", "confidence": 0.9, "reason": self.reason}, ensure_ascii=False)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]},
                              request=httpx.Request("POST", url))


TAMIL = [{"phrase_id": i + 1, "text": t, "score": 80.0 - 5 * i, "urgent": False, "composed": False,
          "parts": {"similarity": 80.0 - 5 * i}} for i, t in enumerate(["தண்ணி வேணும்", "பால் வேணும்", "டீ குடிக்கணும்"])]


@pytest.fixture
def judged(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setattr(llm_judge, "_cache", {})

    def run(reason, reason_language):
        fake = FakeLLM(reason)
        monkeypatch.setattr(llm_judge.httpx, "post", fake)
        return llm_judge.judge("பால் வேனும்", TAMIL, "home", [], {}, 1, "ta", reason_language), fake.bodies[0]
    return run


def test_the_judge_is_told_the_language_and_answers_in_the_interface_language(judged):
    result, body = judged("பால் போல ஒலிக்கிறது", "ta")
    message = body["messages"][1]["content"]
    assert message.startswith("the person speaks tamil, written in tamil script. the stt registered: பால் வேனும்")
    assert message.endswith("write the reason in tamil.") and body["messages"][0]["content"] == llm_judge.SYSTEM
    candidates = json.loads(message.split("(best first): ")[1].split(". context: ")[0])
    assert candidates[1] == {"id": "2", "native": "பால் வேணும்", "latin": "paal venum", "meaning_en": "I need milk",
                             "score": 0.75, "times_used": 0}
    assert result["chosen_by"] == "judge" and result["reason"] == "பால் போல ஒலிக்கிறது"
    assert result["shown"][0]["text"] == "பால் வேணும்"


@pytest.mark.parametrize("reason, reason_language", [
    ("sounds like paal venum", "ta"),  # not in the interface's script
    ("{\"x\": 1}", "en"),
    ("", "en"),
    ("123 !!", "en"),
])
def test_a_reason_that_isnt_readable_text_is_not_shown(judged, reason, reason_language):
    result, _ = judged(reason, reason_language)
    assert result["chosen_by"] == "judge" and result["reason"] is None


def test_the_recognize_route_passes_the_interface_language_to_the_judge(env, monkeypatch):
    seen = []
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("LLM_MODE", "always")
    monkeypatch.setattr(llm_judge, "judge", lambda *args: seen.append(args[-2:]) or {
        "shown": args[1][:3], "chosen_by": "matcher", "reason": None})
    client = env.signup("bn")
    for text in ("জল চাই", "দুধ চাই"):
        env.enroll_phrase(client, text)
    env.fake.transcripts.append("জল চাই")
    client.post("/me/recognize", data={"ui_language": "hi"}, files=env.recording()).raise_for_status()
    assert seen == [("bn", "hi")]


# --- easier alternatives


def test_alternatives_in_other_languages_only_ask_groq_with_the_language(env, monkeypatch):
    import trainings

    monkeypatch.setenv("LLM_ENABLED", "1")
    asked = []
    monkeypatch.setattr(trainings, "call_groq_alternatives", lambda text, lang, tricky: asked.append(lang) or None)
    client = env.signup("ta")
    answer = client.post("/me/trainings/alternatives", json={"text": "பானி சாஹியே", "lang": "ta"}).json()
    assert asked == ["ta"] and answer["alternatives"] == []
