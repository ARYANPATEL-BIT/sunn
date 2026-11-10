import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

import db
from conftest import EMBEDDING, wav


def phrase_id(client, text):
    return next(p["id"] for p in client.get("/me/phrases").json() if p["text"] == text)


def block_id(client, path, text):
    return next(b["id"] for b in client.get(path).json() if b["text"] == text)


def files_under(folder):
    return [p for p in Path(folder).rglob("*") if p.is_file()] if os.path.exists(folder) else []


# --- accounts ---

def test_signup_login_logout(env):
    client = env.client()
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    body = {"name": "Asha", "email": email, "password": "password123", "language": "hi"}
    assert client.post("/auth/signup", json=body).json()["error"] == "consent_required"
    user = client.post("/auth/signup", json={**body, "consent": True}).json()
    assert user["email"] == email and user["use_own_voice"] is False and "voice_embedding" not in user
    assert env.client().post("/auth/signup", json={**body, "consent": True}).json()["error"] == "email_taken"
    assert client.get("/auth/me").json()["id"] == user["id"]

    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/login", json={"email": email, "password": "wrong-password"}).json()["error"] == "bad_login"
    assert client.post("/auth/login", json={"email": email.upper(), "password": "password123"}).status_code == 200
    assert client.get("/auth/me").json()["id"] == user["id"]


def test_signup_seeds_building_blocks_in_the_users_language(env):
    hi, en = env.signup("hi"), env.signup("en")
    assert [w["text"] for w in hi.get("/me/slot-words").json()] == ["पानी", "दवाई", "खाना", "चाय", "कंबल",
                                                                     "बेटे", "बेटी", "डॉक्टर", "नर्स"]
    assert [(t["text"], t["slot"], t["fixed_part"]) for t in hi.get("/me/templates").json()] == [
        ("{item} चाहिए", "item", "चाहिए"), ("{person} को बुलाओ", "person", "को बुलाओ")]
    assert [t["fixed_part"] for t in en.get("/me/templates").json()] == ["I need", "Call"]


def test_google_auth_signup_and_login(env):
    client = env.client()
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "iss": "https://accounts.google.com",
        "sub": "google-sub-999",
        "email": "unique_google_user@example.com",
        "email_verified": "true",
        "name": "Google Tester",
    }

    with patch("requests.get", return_value=mock_res):
        # 1. New user registration via Google
        res = client.post("/auth/google", json={"id_token": "mock-token-xyz", "language": "hi", "consent": True})
        assert res.status_code == 200
        user = res.json()
        assert user["email"] == "unique_google_user@example.com"
        assert user["name"] == "Google Tester"
        assert user["language"] == "hi"

        # Check authenticated session
        me = client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["id"] == user["id"]

        # 2. Existing user logging in via Google
        client2 = env.client()
        res2 = client2.post("/auth/google", json={"id_token": "mock-token-xyz"})
        assert res2.status_code == 200
        assert res2.json()["id"] == user["id"]


def test_google_auth_invalid_tokens_and_lockout(env, monkeypatch):
    client = env.client()

    # Empty token
    assert client.post("/auth/google", json={"id_token": "   "}).status_code == 400

    # Expired / invalid token from Google
    mock_err = MagicMock()
    mock_err.status_code = 400
    mock_err.json.return_value = {"error_description": "Invalid Value"}
    with patch("requests.get", return_value=mock_err):
        res = client.post("/auth/google", json={"id_token": "bad-token"})
        assert res.status_code == 401
        assert res.json()["error"] == "invalid_google_token"

    # Unverified email
    mock_unverified = MagicMock()
    mock_unverified.status_code = 200
    mock_unverified.json.return_value = {
        "iss": "https://accounts.google.com",
        "sub": "sub-111",
        "email": "unverified@example.com",
        "email_verified": "false",
    }
    with patch("requests.get", return_value=mock_unverified):
        res = client.post("/auth/google", json={"id_token": "unverified-token", "consent": True})
        assert res.status_code == 400
        assert res.json()["error"] == "unverified_email"

    # Audience mismatch when GOOGLE_CLIENT_ID is configured
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "expected-client-id")
    mock_mismatch = MagicMock()
    mock_mismatch.status_code = 200
    mock_mismatch.json.return_value = {
        "iss": "https://accounts.google.com",
        "sub": "sub-111",
        "aud": "wrong-client-id",
        "email": "aud@example.com",
        "email_verified": "true",
    }
    with patch("requests.get", return_value=mock_mismatch):
        res = client.post("/auth/google", json={"id_token": "token", "consent": True})
        assert res.status_code == 401
        assert res.json()["error"] == "invalid_google_token"




def test_google_auth_password_login_refused_gracefully(env):
    client = env.client()
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "iss": "https://accounts.google.com",
        "sub": "google-pwd-test",
        "email": "nopassword@example.com",
        "email_verified": "true",
        "name": "No Password",
    }

    with patch("requests.get", return_value=mock_res):
        client.post("/auth/google", json={"id_token": "token", "consent": True})

    # User exists with oauth:google hash; password login should fail with bad_login and not 500
    login_attempt = client.post("/auth/login", json={"email": "nopassword@example.com", "password": "anypassword"})
    assert login_attempt.status_code == 401
    assert login_attempt.json()["error"] == "bad_login"


def test_default_phrases_get_contexts_and_urgency(env):
    phrases = {p["text"]: p for p in env.signup("hi").get("/me/phrases").json()}
    assert phrases["दर्द हो रहा है"]["contexts"] == ["hospital"] and phrases["दर्द हो रहा है"]["urgent"]
    assert phrases["मदद चाहिए"]["contexts"] == ["any"] and phrases["मदद चाहिए"]["urgent"]
    assert phrases["पानी चाहिए"]["contexts"] == ["home", "hospital"] and not phrases["पानी चाहिए"]["urgent"]
    english = {p["text"]: p for p in env.signup("en").get("/me/phrases").json()}
    assert english["I'm in pain"]["urgent"] and english["I need help"]["urgent"]


def test_one_user_can_never_read_or_change_another_users_data(env):
    alice, bob = env.signup(), env.signup()
    alice_phrase = phrase_id(alice, "पानी चाहिए")
    env.enroll_phrase(alice, "पानी चाहिए")
    heard = env.recognize(alice, "पानी चाहिए")
    alice_word = block_id(alice, "/me/slot-words", "चाय")
    alice_template = block_id(alice, "/me/templates", "{item} चाहिए")
    alice_sample = heard["sample_id"]
    before = alice.get("/me/phrases").json()

    for method, path, kwargs in [
        ("patch", f"/me/phrases/{alice_phrase}", {"json": {"text": "hacked"}}),
        ("delete", f"/me/phrases/{alice_phrase}", {}),
        ("delete", f"/me/samples/{alice_sample}", {}),
        ("delete", f"/me/slot-words/{alice_word}", {}),
        ("delete", f"/me/templates/{alice_template}", {}),
        ("post", "/me/enroll", {"data": {"phrase_id": alice_phrase}, "files": env.recording()}),
        ("post", f"/me/slot-words/{alice_word}/enroll", {"files": env.recording()}),
        ("post", f"/me/templates/{alice_template}/enroll", {"files": env.recording()}),
        ("post", "/me/confirm", {"json": {"sample_id": alice_sample, "phrase_id": phrase_id(bob, "पानी चाहिए")}}),
        ("post", "/me/confirm", {"json": {"sample_id": heard["sample_id"] + 1000, "phrase_id": alice_phrase}}),
    ]:
        response = getattr(bob, method)(path, **kwargs)
        assert response.status_code == 404, (method, path, response.text)

    # bob's own sample, confirmed as alice's phrase or alice's template, is refused too
    own = env.recognize(bob, "पानी")
    assert bob.post("/me/confirm", json={"sample_id": own["sample_id"], "phrase_id": alice_phrase}).status_code == 404
    assert bob.post("/me/confirm", json={"sample_id": own["sample_id"], "template_id": alice_template,
                                         "slot_word_id": block_id(bob, "/me/slot-words", "चाय")}).status_code == 404
    assert alice_phrase not in [p["id"] for p in bob.get("/me/phrases").json()]
    assert alice_word not in [w["id"] for w in bob.get("/me/slot-words").json()]
    assert alice.get("/me/phrases").json() == before
    assert env.client().get("/me/phrases").status_code == 401  # and nobody at all without a session


def test_routes_without_ids_only_ever_touch_the_signed_in_user(env):
    """The list, stats, speak and account routes take the user from the cookie alone."""
    alice, bob = env.signup(), env.signup()
    alice.post("/me/templates", json={"text": "{place} ले चलो"})
    env.enroll_phrase(alice, "पानी चाहिए", "paani")
    alice_heard = env.recognize(alice, "paani")
    alice.post("/me/confirm", json={"sample_id": alice_heard["sample_id"], "phrase_id": phrase_id(alice, "पानी चाहिए")})
    alice.post("/me/voice", data={"consent": "true"}, files=env.recording(6))
    alice.patch("/me", json={"caregiver_name": "Ravi", "caregiver_phone": "919876543210", "use_own_voice": True})
    before = {path: alice.get(path).json() for path in
              ("/auth/me", "/me/phrases", "/me/slot-words", "/me/templates", "/me/stats")}

    assert "{place} ले चलो" not in [t["text"] for t in bob.get("/me/templates").json()]
    stats = bob.get("/me/stats").json()
    assert stats["confirmed"] == 0 and stats["top_phrases"] == []
    # bob has nothing enrolled, so alice's fingerprint for the same words is never a candidate
    assert env.recognize(bob, "paani")["candidates"] == []
    assert bob.post("/speak", json={"text": "पानी चाहिए"}).status_code == 200  # the stock voice, not alice's
    assert env.fake.sent("tts")[-1]["json"]["model"] == "timbre-v2.5"

    assert bob.delete("/me/voice").json()["has_own_voice"] is False
    assert bob.patch("/me", json={"caregiver_name": None, "language": "en"}).status_code == 200
    assert bob.delete("/me").status_code == 200
    assert {path: alice.get(path).json() for path in before} == before


# --- recognition ---

def test_recognize_returns_score_parts_urgency_and_context_boost(env):
    client = env.signup()
    env.enroll_phrase(client, "दर्द हो रहा है")
    env.enroll_phrase(client, "सिर में दर्द है")
    result = env.recognize(client, "दर्द हो रहा", context="hospital")
    top = result["candidates"][0]
    assert top["text"] == "दर्द हो रहा है" and top["urgent"] is True and top["composed"] is False
    assert top["parts"]["context"] == 6 and top["parts"]["freq"] == 0 and top["parts"]["time"] == 0
    assert top["score"] == round(sum(top["parts"].values()), 1)
    assert result["context"] == "hospital" and result["low_confidence"] is False
    assert client.post("/me/recognize", data={"context": "office"}, files=env.recording()).json()["error"] == "invalid_input"


def test_confirmed_uses_add_frequency_and_time_boosts(env):
    client = env.signup()
    phrase = env.enroll_phrase(client, "चाय पीनी है")
    for _ in range(2):
        heard = env.recognize(client, "चाय पीनी")
        assert client.post("/me/confirm", json={"sample_id": heard["sample_id"], "phrase_id": phrase["id"]}).is_success
    top = env.recognize(client, "चाय पीनी")["candidates"][0]
    assert top["parts"]["freq"] == 4 and top["parts"]["time"] == 3
    used = next(p for p in client.get("/me/phrases").json() if p["id"] == phrase["id"])
    assert used["sample_count"] == 3 and used["enrolled"] == 1 and used["last_used_at"]


def test_composed_candidate_is_built_from_blocks_and_becomes_a_phrase(env):
    client = env.signup()
    word, template = block_id(client, "/me/slot-words", "चाय"), block_id(client, "/me/templates", "{item} चाहिए")
    env.enroll(client, f"/me/slot-words/{word}/enroll", "चाय")
    env.enroll(client, f"/me/templates/{template}/enroll", "चाहिए")
    assert next(w for w in client.get("/me/slot-words").json() if w["id"] == word)["enrolled"] == 1

    heard = env.recognize(client, "चाय चाहिए")
    top = heard["candidates"][0]
    assert top == {"phrase_id": None, "text": "चाय चाहिए", "score": 100.0, "urgent": False, "composed": True,
                   "template_id": template, "slot_word_id": word,
                   "parts": {"similarity": 100.0, "context": 0, "freq": 0.0, "time": 0.0}}

    confirmed = client.post("/me/confirm", json={"sample_id": heard["sample_id"], "template_id": template,
                                                 "slot_word_id": word}).json()
    assert confirmed["text"] == "चाय चाहिए"
    again = env.recognize(client, "चाय चाहिए")["candidates"][0]
    assert again["phrase_id"] == confirmed["phrase_id"] and again["composed"] is False
    assert [c["text"] for c in env.recognize(client, "चाय चाहिए")["candidates"]].count("चाय चाहिए") == 1


def test_composed_text_that_is_already_a_phrase_counts_as_that_phrase(env):
    client = env.signup()
    word, template = block_id(client, "/me/slot-words", "पानी"), block_id(client, "/me/templates", "{item} चाहिए")
    env.enroll(client, f"/me/slot-words/{word}/enroll", "पानी")
    env.enroll(client, f"/me/templates/{template}/enroll", "चाहिए")
    top = env.recognize(client, "पानी चाहिए")["candidates"][0]
    assert top["phrase_id"] == phrase_id(client, "पानी चाहिए") and top["composed"] is False


def test_composed_english_puts_the_fixed_part_first(env):
    client = env.signup("en")
    word, template = block_id(client, "/me/slot-words", "the nurse"), block_id(client, "/me/templates", "Call {person}")
    env.enroll(client, f"/me/slot-words/{word}/enroll", "the nurse")
    env.enroll(client, f"/me/templates/{template}/enroll", "call")
    top = env.recognize(client, "call the nurse")["candidates"][0]
    assert top["text"] == "Call the nurse" and top["composed"] and top["parts"]["similarity"] == 100


def test_confirm_needs_exactly_one_answer(env):
    client = env.signup()
    heard = env.recognize(client, "पानी")
    for body in ({}, {"phrase_id": 1, "new_text": "x"}, {"template_id": 1}, {"phrase_id": 1, "slot_word_id": 1}):
        assert client.post("/me/confirm", json={"sample_id": heard["sample_id"], **body}).json()["error"] == "invalid_input"
    word = block_id(client, "/me/slot-words", "बेटी")  # a person, but this template takes an item
    template = block_id(client, "/me/templates", "{item} चाहिए")
    assert client.post("/me/confirm", json={"sample_id": heard["sample_id"], "template_id": template,
                                            "slot_word_id": word}).json()["error"] == "invalid_input"


# --- uploads and Gnani ---

def test_upload_limits_and_no_speech(env):
    client = env.signup()
    pid = phrase_id(client, "पानी चाहिए")
    enroll = lambda files: client.post("/me/enroll", data={"phrase_id": pid}, files=files).json()  # noqa: E731
    assert enroll(env.recording(16))["error"] == "audio_too_long"
    assert enroll(env.recording(0.1))["error"] == "audio_too_short"
    assert enroll({"audio": ("big.wav", b"\0" * (10 * 2**20 + 1), "audio/wav")})["error"] == "file_too_large"
    # far over the limit: refused from Content-Length alone, before the body is read
    huge = enroll({"audio": ("huge.wav", b"\0" * (11 * 2**20), "audio/wav")})
    assert huge["error"] == "file_too_large" and huge["message"].startswith("the upload is over")
    assert enroll({"audio": ("junk.wav", b"not audio", "audio/wav")})["error"] == "bad_audio"
    env.fake.transcripts.append("  ")
    assert enroll(env.recording())["error"] == "no_speech"
    assert len(env.fake.sent("stt")) == 1  # only the recording that passed the checks was sent
    assert db.row("SELECT COUNT(*) AS n FROM samples")["n"] == 0
    assert files_under("data/users") == []  # nothing left behind


def test_gnani_retries_once_then_gives_a_clear_code(env):
    client = env.signup()
    pid = phrase_id(client, "पानी चाहिए")
    enroll = lambda: client.post("/me/enroll", data={"phrase_id": pid}, files=env.recording())  # noqa: E731

    env.fake.failures, env.fake.transcripts = [503], ["पानी चाहिए"]
    assert enroll().status_code == 200 and len(env.fake.sent("stt")) == 2

    env.fake.failures = [requests.Timeout(), requests.ConnectionError()]
    response = enroll()
    assert response.status_code == 502
    assert response.json() | {"message": ""} == {"error": "gnani_unreachable", "message": ""}
    assert len(env.fake.sent("stt")) == 4

    env.fake.failures = [400]
    assert enroll().json()["error"] == "gnani_rejected" and len(env.fake.sent("stt")) == 5  # no retry on 4xx
    assert db.row("SELECT COUNT(*) AS n FROM api_calls WHERE kind = 'stt' AND cached = 0")["n"] == 5


def test_credit_limit_refuses_new_calls_but_not_cached_ones(env, monkeypatch):
    client = env.signup()
    pid = phrase_id(client, "पानी चाहिए")
    monkeypatch.setenv("GNANI_CALL_LIMIT", "1")
    first = env.recording()
    env.fake.transcripts.append("पानी चाहिए")
    assert client.post("/me/enroll", data={"phrase_id": pid}, files=first).status_code == 200

    refused = client.post("/me/enroll", data={"phrase_id": pid}, files=env.recording())
    assert refused.status_code == 429 and refused.json()["error"] == "credit_limit_reached"
    assert client.post("/speak", json={"text": "नमस्ते"}).json()["error"] == "credit_limit_reached"
    assert client.post("/me/enroll", data={"phrase_id": pid}, files=first).status_code == 200  # cached
    assert len(env.fake.requests) == 1
    assert db.row("SELECT SUM(cached = 0) AS sent, SUM(cached) AS cached FROM api_calls") == {"sent": 1, "cached": 1}




def test_deleting_an_account_unties_its_calls(env):
    client = env.signup()
    env.enroll_phrase(client, "पानी चाहिए")
    assert db.row("SELECT user_id FROM api_calls")["user_id"] == client.get("/auth/me").json()["id"]
    client.delete("/me").raise_for_status()
    assert db.rows("SELECT user_id, cached FROM api_calls") == [{"user_id": None, "cached": 0}]


def test_demo_recordings_keep_their_source(env):
    client = env.signup()
    pid = phrase_id(client, "पानी चाहिए")
    env.fake.transcripts += ["पानी चाहिए", "पानी चाहिए", "पानी"]
    simulated = client.post("/me/enroll", data={"phrase_id": pid, "source": "simulated"}, files=env.recording())
    assert simulated.json()["source"] == "simulated"
    assert client.post("/me/enroll", data={"phrase_id": pid}, files=env.recording()).json()["source"] is None
    word = client.get("/me/slot-words").json()[0]
    assert client.post(f"/me/slot-words/{word['id']}/enroll", data={"source": "pilot"},
                       files=env.recording()).json()["source"] == "pilot"

    phrases = client.get("/me/phrases").json()
    assert [p["sources"] for p in phrases if p["id"] == pid] == [["simulated"]]
    assert all(p["sources"] == [] for p in phrases if p["id"] != pid)
    refused = client.post("/me/enroll", data={"phrase_id": pid, "source": "real"}, files=env.recording())
    assert refused.status_code == 422 and refused.json()["error"] == "invalid_input"
    assert len(env.fake.sent("stt")) == 3  # refused before Prisma


def test_server_usage_is_for_the_owner_only(env, monkeypatch):
    client = env.signup()
    assert client.get("/admin/usage").json()["error"] == "not_owner"
    monkeypatch.setenv("OWNER_EMAIL", client.get("/auth/me").json()["email"].upper())
    env.enroll_phrase(client, "पानी चाहिए")
    usage = client.get("/admin/usage").json()
    assert usage["limit"] == 4000 and usage["sent"] == 1 and usage["remaining"] == 3999
    assert usage["by_kind"]["stt"]["sent"] == 1 and usage["by_kind"]["stt"]["sent_audio_seconds"] == 1.0
    assert env.signup().get("/admin/usage").status_code == 403


# --- own voice ---

def test_own_voice(env):
    client = env.signup()
    voice = lambda seconds, consent="true": client.post(  # noqa: E731
        "/me/voice", data={"consent": consent}, files={"audio": ("me.wav", wav(seconds, 330), "audio/wav")})
    assert voice(6, consent="").json()["error"] == "consent_required"
    assert voice(4).json()["error"] == "audio_too_short"
    assert voice(31).json()["error"] == "audio_too_long"
    assert client.patch("/me", json={"use_own_voice": True}).json()["error"] == "no_voice"

    assert voice(6).json()["has_own_voice"] is True
    sent = env.fake.sent("clone")
    assert len(sent) == 1 and sent[0]["files"]["audio_file"][0] == "voice.wav"
    assert abs(len(sent[0]["files"]["audio_file"][1]) - (44 + 6 * 44100 * 2)) < 1000  # 6 s, 44.1 kHz mono
    assert voice(6).status_code == 200 and len(env.fake.sent("clone")) == 1  # same audio: cached
    assert client.get("/auth/me").json()["use_own_voice"] is False  # off until the user turns it on

    stock = client.post("/speak", json={"text": "पानी चाहिए"})
    assert stock.headers["content-type"] == "audio/wav"
    assert client.patch("/me", json={"use_own_voice": True}).json()["use_own_voice"] is True
    client.post("/speak", json={"text": "पानी चाहिए"})
    client.post("/speak", json={"text": "पानी चाहिए"})
    bodies = [r["json"] for r in env.fake.sent("tts")]
    assert len(bodies) == 2  # the voice is part of the cache key; the repeat was cached
    assert bodies[0]["voice"] == "Nalini" and "speaker_embedding" not in bodies[0]
    assert bodies[1]["speaker_embedding"] == EMBEDDING and bodies[1]["model"] == "vachana-vc-v1"

    user_id = client.get("/auth/me").json()["id"]
    assert files_under(f"data/users/{user_id}/voice")  # the embedding cache and the cloned speech
    removed = client.delete("/me/voice").json()
    assert removed["has_own_voice"] is False and removed["use_own_voice"] is False
    assert not os.path.exists(f"data/users/{user_id}/voice")
    client.post("/speak", json={"text": "पानी चाहिए"})
    assert len(env.fake.sent("tts")) == 2  # back to the stock voice, still cached


def test_caregiver_details(env):
    client = env.signup()
    me = client.patch("/me", json={"caregiver_name": " Ravi ", "caregiver_phone": "+91 98765-43210"}).json()
    assert me["caregiver_name"] == "Ravi" and me["caregiver_phone"] == "919876543210"
    assert client.patch("/me", json={"caregiver_phone": "12345"}).json()["error"] == "invalid_input"
    assert client.patch("/me", json={"email": "x@example.com"}).json()["error"] == "invalid_input"
    assert client.patch("/me", json={"caregiver_phone": None}).json()["caregiver_phone"] is None


# --- phrase management ---

def test_edit_and_delete_phrases_and_samples(env):
    client = env.signup()
    phrase = env.enroll_phrase(client, "पानी चाहिए")
    edited = client.patch(f"/me/phrases/{phrase['id']}", json={
        "text": "ठंडा पानी चाहिए", "contexts": ["home", "market"], "urgent": True}).json()
    assert edited == {"id": phrase["id"], "text": "ठंडा पानी चाहिए", "contexts": ["home", "market"], "urgent": True,
                      "language": "hi"}
    assert client.patch(f"/me/phrases/{phrase['id']}", json={"contexts": ["office"]}).json()["error"] == "invalid_input"
    assert client.patch(f"/me/phrases/{phrase['id']}", json={"text": "नमस्ते"}).json()["error"] == "phrase_exists"

    heard = env.recognize(client, "ठंडा पानी")
    client.post("/me/confirm", json={"sample_id": heard["sample_id"], "phrase_id": phrase["id"]})
    other = env.recognize(client, "ठंडा पानी")  # its top1 points at the phrase, and must not block deleting it
    user_id = client.get("/auth/me").json()["id"]
    assert len(files_under(f"data/users/{user_id}")) == 3 and len(files_under("data/cache/prisma")) == 3

    assert client.delete(f"/me/phrases/{phrase['id']}").json() == {"ok": True}
    assert phrase["id"] not in [p["id"] for p in client.get("/me/phrases").json()]
    assert db.row("SELECT COUNT(*) AS n FROM uses")["n"] == 0
    assert len(files_under(f"data/users/{user_id}")) == 1 and len(files_under("data/cache/prisma")) == 1

    assert client.delete(f"/me/samples/{other['sample_id']}").json() == {"ok": True}
    assert files_under(f"data/users/{user_id}") == [] and files_under("data/cache/prisma") == []
    assert client.delete(f"/me/samples/{other['sample_id']}").status_code == 404


def test_delete_slot_words_and_templates_with_their_recordings(env):
    client = env.signup()
    word, template = block_id(client, "/me/slot-words", "चाय"), block_id(client, "/me/templates", "{item} चाहिए")
    env.enroll(client, f"/me/slot-words/{word}/enroll", "चाय")
    env.enroll(client, f"/me/templates/{template}/enroll", "चाहिए")
    assert client.post("/me/templates", json={"text": "मुझे {item} दो"}).json()["error"] == "invalid_input"
    assert client.post("/me/templates", json={"text": "{place} जाना है"}).json()["fixed_part"] == "जाना है"
    assert client.post("/me/slot-words", json={"slot": "place", "text": "बाज़ार"}).json()["enrolled"] == 0
    client.delete(f"/me/slot-words/{word}")
    client.delete(f"/me/templates/{template}")
    assert db.row("SELECT COUNT(*) AS n FROM samples")["n"] == 0 and files_under("data/users") == []


# --- progress ---

def test_stats(env):
    client = env.signup()
    water, tea = env.enroll_phrase(client, "पानी चाहिए"), env.enroll_phrase(client, "चाय पीनी है")
    for transcript, phrase in [("पानी चाहिए", water), ("पानी", water), ("चाय पीनी है", tea)]:
        heard = env.recognize(client, transcript)
        client.post("/me/confirm", json={"sample_id": heard["sample_id"], "phrase_id": phrase["id"]})
    env.recognize(client, "कुछ और")  # never confirmed

    stats = client.get("/me/stats").json()
    assert (stats["phrases"], stats["samples"], stats["recognitions"], stats["confirmed"]) == (51, 5, 4, 3)
    weeks = stats["clear_without_help_by_week"]
    assert len(weeks) == 8 and weeks[0]["week_start"] < weeks[-1]["week_start"]
    assert weeks[-1] | {"week_start": None} == {"week_start": None, "confirmed": 3, "clear": 2, "rate": 0.667}
    assert all(w["rate"] is None for w in weeks[:-1])
    assert [(p["text"], p["uses"]) for p in stats["top_phrases"]] == [("पानी चाहिए", 2), ("चाय पीनी है", 1)]


# --- deleting the account ---

def test_delete_me_removes_everything(env):
    client = env.signup()
    other = env.signup()
    env.enroll_phrase(other, "पानी चाहिए")
    user_id = client.get("/auth/me").json()["id"]

    phrase = env.enroll_phrase(client, "पानी चाहिए")
    env.enroll(client, f"/me/slot-words/{block_id(client, '/me/slot-words', 'चाय')}/enroll", "चाय")
    heard = env.recognize(client, "पानी")
    client.post("/me/confirm", json={"sample_id": heard["sample_id"], "phrase_id": phrase["id"]})
    client.post("/me/voice", data={"consent": "true"}, files={"audio": ("me.wav", wav(6, 330), "audio/wav")})
    client.patch("/me", json={"use_own_voice": True})
    client.post("/speak", json={"text": "पानी चाहिए"})
    assert len(files_under(f"data/users/{user_id}")) == 5  # 3 recordings, the voice embedding, its speech
    assert len(files_under("data/cache/prisma")) == 4

    response = client.delete("/me")
    assert response.json() == {"ok": True}
    assert 'sunn_session=""' in response.headers["set-cookie"]
    assert client.get("/auth/me").status_code == 401
    assert not os.path.exists(f"data/users/{user_id}")
    assert len(files_under("data/cache/prisma")) == 1  # only the other user's
    for table in ("users", "phrases", "samples", "uses", "slot_words", "templates"):
        column = "id" if table == "users" else "user_id"
        assert db.row(f"SELECT COUNT(*) AS n FROM {table} WHERE {column} = ?", (user_id,))["n"] == 0, table
    assert other.get("/me/phrases").json()[1]["enrolled"] == 1  # the other user is untouched
