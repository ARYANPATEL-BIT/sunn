import os
import db
from conftest import wav


def test_cross_user_phrase_isolation(env):
    """Phrases are private to each user: another user cannot see, edit or delete them."""
    client_a = env.signup(language="en")
    client_b = env.signup(language="en")

    created = client_a.post("/me/phrases", json={"text": "Private secret message"}).json()
    phrase_id = created["id"]

    # User B cannot see User A's phrase
    b_phrases = client_b.get("/me/phrases").json()
    assert not any(p["id"] == phrase_id for p in b_phrases)

    # User B cannot edit User A's phrase
    patch_resp = client_b.patch(f"/me/phrases/{phrase_id}", json={"text": "Hacked message"})
    assert patch_resp.status_code == 404
    assert patch_resp.json()["error"] == "not_found"

    # User B cannot delete User A's phrase
    del_resp = client_b.delete(f"/me/phrases/{phrase_id}")
    assert del_resp.status_code == 404
    assert del_resp.json()["error"] == "not_found"

    # User A's phrase remains intact
    a_phrases = client_a.get("/me/phrases").json()
    assert any(p["id"] == phrase_id and p["text"] == "Private secret message" for p in a_phrases)


def test_cross_user_sample_and_entity_isolation(env):
    """Audio recordings, enrollment samples, slot words, and templates are isolated."""
    client_a = env.signup(language="en")
    client_b = env.signup(language="en")

    # User A creates a phrase and enrolls a sample
    phrase_a = client_a.post("/me/phrases", json={"text": "Water please"}).json()
    env.fake.transcripts.append("water please")
    enroll_a = client_a.post("/me/enroll", data={"phrase_id": phrase_a["id"]}, files=env.recording()).json()
    sample_a_id = enroll_a["sample_id"]

    # User B cannot enroll into User A's phrase
    b_enroll = client_b.post("/me/enroll", data={"phrase_id": phrase_a["id"]}, files=env.recording())
    assert b_enroll.status_code == 404
    assert b_enroll.json()["error"] == "not_found"

    # User B cannot delete User A's sample
    del_sample = client_b.delete(f"/me/samples/{sample_a_id}")
    assert del_sample.status_code == 404
    assert del_sample.json()["error"] == "not_found"

    # User A creates a custom slot word
    slot_word_a = client_a.post("/me/slot-words", json={"slot": "item", "text": "pencil"}).json()
    # User B cannot enroll or delete User A's slot word
    b_word_enroll = client_b.post(f"/me/slot-words/{slot_word_a['id']}/enroll", files=env.recording())
    assert b_word_enroll.status_code == 404
    b_word_del = client_b.delete(f"/me/slot-words/{slot_word_a['id']}")
    assert b_word_del.status_code == 404

    # User A creates a custom template
    template_a = client_a.post("/me/templates", json={"text": "give me {item}"}).json()
    # User B cannot enroll or delete User A's template
    b_tpl_enroll = client_b.post(f"/me/templates/{template_a['id']}/enroll", files=env.recording())
    assert b_tpl_enroll.status_code == 404
    b_tpl_del = client_b.delete(f"/me/templates/{template_a['id']}")
    assert b_tpl_del.status_code == 404

    # User B cannot confirm User A's recognition sample
    rec_a = env.recognize(client_a, "water please")
    b_confirm = client_b.post("/me/confirm", json={"sample_id": rec_a["sample_id"], "new_text": "Water please"})
    assert b_confirm.status_code == 404
    assert b_confirm.json()["error"] == "not_found"


def test_consent_enforcement_for_signup_and_voice_cloning(env):
    """Explicit consent is required for signup and voice cloning."""
    client = env.client()

    # Signup without consent is rejected
    signup_fail = client.post("/auth/signup", json={
        "name": "NoConsent", "email": "noconsent@example.com", "password": "password123",
        "language": "en", "consent": False
    })
    assert signup_fail.status_code == 400
    assert signup_fail.json()["error"] == "consent_required"

    # Signup with consent succeeds
    signup_ok = client.post("/auth/signup", json={
        "name": "Consented", "email": "consented@example.com", "password": "password123",
        "language": "en", "consent": True
    })
    assert signup_ok.status_code == 200

    # Voice clone without consent is rejected
    voice_fail = client.post("/me/voice", data={"consent": "false"}, files={"audio": ("voice.wav", wav(6.0), "audio/wav")})
    assert voice_fail.status_code == 400
    assert voice_fail.json()["error"] == "consent_required"

    voice_no_consent = client.post("/me/voice", data={"consent": ""}, files={"audio": ("voice.wav", wav(6.0), "audio/wav")})
    assert voice_no_consent.status_code == 400
    assert voice_no_consent.json()["error"] == "consent_required"

    # Voice clone with consent succeeds and records consent timestamp
    voice_ok = client.post("/me/voice", data={"consent": "true"}, files={"audio": ("voice.wav", wav(6.0), "audio/wav")})
    assert voice_ok.status_code == 200
    me = client.get("/auth/me").json()
    assert me["has_own_voice"] is True

    user_row = db.row("SELECT voice_consent_given_at FROM users WHERE email = 'consented@example.com'")
    assert user_row["voice_consent_given_at"] is not None


def test_account_deletion_cleans_up_all_user_data(env):
    """Deleting an account purges user directory, audio files, and database records."""
    client_a = env.signup(language="en")
    client_b = env.signup(language="en")

    me_a = client_a.get("/auth/me").json()
    user_a_id = me_a["id"]
    me_b = client_b.get("/auth/me").json()
    user_b_id = me_b["id"]

    # User A records an enrollment sample and clones voice
    phrase_a = client_a.post("/me/phrases", json={"text": "Clean me up"}).json()
    env.fake.transcripts.append("clean me up")
    client_a.post("/me/enroll", data={"phrase_id": phrase_a["id"]}, files=env.recording())
    client_a.post("/me/voice", data={"consent": "true"}, files={"audio": ("voice.wav", wav(6.0), "audio/wav")})

    folder_a = f"data/users/{user_a_id}"
    folder_b = f"data/users/{user_b_id}"
    assert os.path.exists(folder_a)

    # User A calls DELETE /me
    del_resp = client_a.delete("/me")
    assert del_resp.status_code == 200
    assert del_resp.json() == {"ok": True}

    # User A files on disk are completely removed
    assert not os.path.exists(folder_a)

    # User A database records are deleted
    assert db.row("SELECT id FROM users WHERE id = ?", (user_a_id,)) is None
    assert db.row("SELECT id FROM phrases WHERE user_id = ?", (user_a_id,)) is None
    assert db.row("SELECT id FROM samples WHERE user_id = ?", (user_a_id,)) is None
    assert db.row("SELECT id FROM slot_words WHERE user_id = ?", (user_a_id,)) is None
    assert db.row("SELECT id FROM templates WHERE user_id = ?", (user_a_id,)) is None

    # User B remains intact
    assert db.row("SELECT id FROM users WHERE id = ?", (user_b_id,)) is not None
    assert client_b.get("/auth/me").status_code == 200
