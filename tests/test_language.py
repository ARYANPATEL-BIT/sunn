import os
from pathlib import Path

import db
import prisma


def phrase_id(client, text):
    return next(p["id"] for p in client.get("/me/phrases").json() if p["text"] == text)


def cached():
    return sorted(p.name for p in Path(prisma.CACHE_DIR).glob("*.json")) if os.path.exists(prisma.CACHE_DIR) else []


def test_switching_language_keeps_everything_and_new_calls_follow_it(env):
    client = env.signup("hi")
    client.post("/me/phrases", json={"text": "I need help"})  # an English default, added early
    water = env.enroll_phrase(client, "पानी चाहिए")
    word = client.get("/me/slot-words").json()[0]
    template = client.get("/me/templates").json()[0]
    env.enroll(client, f"/me/slot-words/{word['id']}/enroll", "paani")
    env.enroll(client, f"/me/templates/{template['id']}/enroll", "chahiye")
    heard = env.recognize(client, "paani chahiye")
    client.post("/me/confirm", json={"sample_id": heard["sample_id"], "phrase_id": water["id"]}).raise_for_status()
    before = {path: client.get(path).json() for path in ("/me/phrases", "/me/slot-words", "/me/templates")}
    samples = db.rows("SELECT id, language FROM samples ORDER BY id")
    assert [s["language"] for s in samples] == ["hi"] * 4

    user = client.patch("/me", json={"language": "en"}).json()
    assert user["language"] == "en" and client.get("/auth/me").json()["language"] == "en"
    assert db.rows("SELECT id, language FROM samples ORDER BY id") == samples
    after = {path: client.get(path).json() for path in before}
    assert after["/me/slot-words"] == before["/me/slot-words"] and after["/me/templates"] == before["/me/templates"]
    # Same phrases; only sample_count drops, to the samples in the new language (none yet).
    assert [{**p, "sample_count": 0} for p in before["/me/phrases"]] == after["/me/phrases"]
    assert next(p for p in before["/me/phrases"] if p["id"] == water["id"])["sample_count"] == 2

    # The defaults for the new language join the old ones. "I need help" was added while the
    # user spoke Hindi, so it is a Hindi phrase; English gets its own.
    help_id = phrase_id(client, "I need help")
    phrases = client.post("/me/phrases/default").json()
    assert len(phrases) == 2 * 51 + 1 and phrase_id(client, "I need help") == help_id
    assert [p["language"] for p in phrases if p["text"] == "I need help"] == ["hi", "en"]
    assert len(client.post("/me/phrases/default").json()) == len(phrases)  # again: nothing new
    assert phrase_id(client, "पानी चाहिए") == water["id"]

    env.enroll_phrase(client, "I need water")
    assert env.fake.sent("stt")[-1]["data"]["language_code"] == "en-IN"
    assert db.row("SELECT language FROM samples ORDER BY id DESC LIMIT 1")["language"] == "en"
    client.post("/speak", json={"text": "I need water"}).raise_for_status()
    assert env.fake.sent("tts")[-1]["json"]["language"] == "en-IN"


def test_default_phrases_add_the_new_languages_building_blocks_too(env):
    import api

    client = env.signup("hi")
    hindi_words, hindi_templates = client.get("/me/slot-words").json(), client.get("/me/templates").json()
    client.patch("/me", json={"language": "en"}).raise_for_status()
    tea = client.post("/me/slot-words", json={"slot": "item", "text": "tea"}).json()
    call = client.post("/me/templates", json={"text": "Call {person}"}).json()

    client.post("/me/phrases/default").raise_for_status()
    words, templates = client.get("/me/slot-words").json(), client.get("/me/templates").json()
    assert words[:len(hindi_words)] == hindi_words and templates[:len(hindi_templates)] == hindi_templates
    english = [(slot, text) for slot, texts in api.DEFAULT_SLOT_WORDS["en"].items() for text in texts]
    assert sorted((w["slot"], w["text"]) for w in words[len(hindi_words):]) == sorted(english)
    assert [t["text"] for t in templates[len(hindi_templates):]] == ["Call {person}", "I need {item}"]
    assert block_ids(words, "tea") == [tea["id"]] and block_ids(templates, "Call {person}") == [call["id"]]

    client.post("/me/phrases/default").raise_for_status()  # again: nothing new
    assert client.get("/me/slot-words").json() == words and client.get("/me/templates").json() == templates


def block_ids(blocks, text):
    return [b["id"] for b in blocks if b["text"] == text]


def test_only_the_ten_languages_are_languages(env):
    client = env.signup("hi")
    assert client.patch("/me", json={"language": "ta"}).json()["language"] == "ta"
    client.patch("/me", json={"language": "hi"}).raise_for_status()
    for language in ("hinglish", "hi-IN", "EN", ""):
        refused = client.patch("/me", json={"language": language})
        assert refused.status_code == 422 and refused.json()["error"] == "invalid_input", language
    assert client.patch("/me", json={"language": None}).json()["language"] == "hi"
    assert client.get("/auth/me").json()["language"] == "hi"


def test_the_matcher_ignores_samples_in_another_language(env):
    client = env.signup("hi")
    water = env.enroll_phrase(client, "पानी चाहिए", "paani chahiye")
    word = next(w for w in client.get("/me/slot-words").json() if w["text"] == "चाय")
    template = client.get("/me/templates").json()[0]
    env.enroll(client, f"/me/slot-words/{word['id']}/enroll", "chai")
    env.enroll(client, f"/me/templates/{template['id']}/enroll", "chahiye")
    hindi = env.recognize(client, "paani chahiye")["candidates"]
    assert hindi[0]["phrase_id"] == water["id"] and any(c["composed"] for c in hindi)

    client.patch("/me", json={"language": "en"}).raise_for_status()
    assert env.recognize(client, "paani chahiye")["candidates"] == []
    client.post("/me/phrases/default").raise_for_status()
    env.enroll_phrase(client, "I need water")
    english = env.recognize(client, "I need water")["candidates"]
    assert [c["text"] for c in english] == ["I need water"]

    # Back to Hindi: the Hindi samples were never deleted, so they count again, and the user's
    # English phrases stay candidates too.
    client.patch("/me", json={"language": "hi"}).raise_for_status()
    hindi_again = env.recognize(client, "paani chahiye")["candidates"]
    assert hindi_again[0]["phrase_id"] == water["id"]
    assert "I need water" in [c["text"] for c in hindi_again]


def test_deleting_an_old_language_sample_removes_its_own_cache_entry(env):
    client = env.signup("hi")
    water = env.enroll_phrase(client, "पानी चाहिए")
    hindi = db.row("SELECT id, audio_path FROM samples WHERE phrase_id = ?", (water["id"],))
    with open(hindi["audio_path"], "rb") as f:
        hindi_cache = os.path.basename(prisma.cache_path(f.read(), "hi"))
    assert cached() == [hindi_cache]

    client.patch("/me", json={"language": "en"}).raise_for_status()
    env.enroll_phrase(client, "पानी चाहिए", "paani chahiye")  # the same phrase, now in English
    english_cache = sorted(set(cached()) - {hindi_cache})
    assert len(english_cache) == 1

    assert client.delete(f"/me/samples/{hindi['id']}").json() == {"ok": True}
    assert cached() == english_cache and not os.path.exists(hindi["audio_path"])

    # Deleting the phrase removes the rest, in whichever language each was transcribed.
    env.enroll(client, f"/me/slot-words/{client.get('/me/slot-words').json()[0]['id']}/enroll", "paani")
    client.patch("/me", json={"language": "hi"}).raise_for_status()
    env.enroll_phrase(client, "पानी चाहिए")
    assert client.delete(f"/me/phrases/{water['id']}").json() == {"ok": True}
    assert len(cached()) == 1  # only the slot word's, in English
    assert client.delete("/me").json() == {"ok": True}
    assert cached() == []


def test_existing_samples_get_their_users_language(env):
    client = env.signup("en")
    env.enroll_phrase(client, "I need water")
    db.execute("UPDATE samples SET language = NULL")
    db.init()
    assert db.row("SELECT language FROM samples")["language"] == "en"
