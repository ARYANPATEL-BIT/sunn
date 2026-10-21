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
